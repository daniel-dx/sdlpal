#!/usr/bin/env python3
"""
仙剑高清方案对比演示 — 使用真实游戏素材
从 MKF 文件提取 FBP（全屏背景图）+ 调色板，对比不同放大算法的效果。
"""

import struct
import zlib
import os
import sys

# ============================================================
# 极简 PNG 写入（不依赖任何第三方库）
# ============================================================

def write_png(filename, pixels, width, height):
    """写入 RGB PNG 文件。pixels 是 [(r,g,b), ...] 长度 width*height"""
    def chunk(chunk_type, data):
        c = chunk_type + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)

    header = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))

    raw = bytearray()
    for y in range(height):
        raw += b'\x00'  # filter: None
        row_start = y * width
        for x in range(width):
            r, g, b = pixels[row_start + x]
            raw += bytes([r, g, b])

    idat = chunk(b'IDAT', zlib.compress(bytes(raw), 9))
    iend = chunk(b'IEND', b'')

    with open(filename, 'wb') as f:
        f.write(header + ihdr + idat + iend)
    print(f"  已写入: {filename} ({width}x{height})")


# ============================================================
# MKF 文件格式读取
# ============================================================

class MKFReader:
    """读取仙剑 MKF 归档文件"""

    def __init__(self, filepath):
        with open(filepath, 'rb') as f:
            self.data = f.read()
        # 偏移表
        first_offset = struct.unpack_from('<I', self.data, 0)[0]
        self.chunk_count = (first_offset - 4) // 4
        self.offsets = []
        for i in range(self.chunk_count + 1):
            self.offsets.append(struct.unpack_from('<I', self.data, i * 4)[0])

    def get_chunk_count(self):
        return self.chunk_count

    def get_chunk_raw(self, idx):
        """读取原始 chunk 数据"""
        if idx >= self.chunk_count:
            return None
        start = self.offsets[idx]
        end = self.offsets[idx + 1]
        if end <= start:
            return None
        return self.data[start:end]

    def get_chunk_decompressed(self, idx):
        """读取并解压 chunk（自动检测 YJ1/YJ2 格式）"""
        raw = self.get_chunk_raw(idx)
        if raw is None:
            return None
        # 检查是否为 YJ1 格式
        if len(raw) >= 4:
            sig = struct.unpack_from('<I', raw, 0)[0]
            if sig == 0x315f4a59:  # 'YJ_1'
                return None  # YJ1 暂未实现
        # 否则为 YJ2 格式（WIN95 版）
        return yj2_decompress(raw)


# ============================================================
# YJ1 解压算法（从 yj1.c 移植）
# ============================================================

def yj2_decompress(data):
    """YJ2 解压算法（WIN95 版）— 从 yj1.c 忠实移植"""

    # YJ2 查找表
    yj2_data1 = bytes([
        0x3f, 0x0b, 0x17, 0x03, 0x2f, 0x0a, 0x16, 0x00, 0x2e, 0x09, 0x15, 0x02, 0x2d, 0x01, 0x08, 0x00,
        0x3e, 0x07, 0x14, 0x03, 0x2c, 0x06, 0x13, 0x00, 0x2b, 0x05, 0x12, 0x02, 0x2a, 0x01, 0x04, 0x00,
        0x3d, 0x0b, 0x11, 0x03, 0x29, 0x0a, 0x10, 0x00, 0x28, 0x09, 0x0f, 0x02, 0x27, 0x01, 0x08, 0x00,
        0x3c, 0x07, 0x0e, 0x03, 0x26, 0x06, 0x0d, 0x00, 0x25, 0x05, 0x0c, 0x02, 0x24, 0x01, 0x04, 0x00,
        0x3b, 0x0b, 0x17, 0x03, 0x23, 0x0a, 0x16, 0x00, 0x22, 0x09, 0x15, 0x02, 0x21, 0x01, 0x08, 0x00,
        0x3a, 0x07, 0x14, 0x03, 0x20, 0x06, 0x13, 0x00, 0x1f, 0x05, 0x12, 0x02, 0x1e, 0x01, 0x04, 0x00,
        0x39, 0x0b, 0x11, 0x03, 0x1d, 0x0a, 0x10, 0x00, 0x1c, 0x09, 0x0f, 0x02, 0x1b, 0x01, 0x08, 0x00,
        0x38, 0x07, 0x0e, 0x03, 0x1a, 0x06, 0x0d, 0x00, 0x19, 0x05, 0x0c, 0x02, 0x18, 0x01, 0x04, 0x00,
        0x37, 0x0b, 0x17, 0x03, 0x2f, 0x0a, 0x16, 0x00, 0x2e, 0x09, 0x15, 0x02, 0x2d, 0x01, 0x08, 0x00,
        0x36, 0x07, 0x14, 0x03, 0x2c, 0x06, 0x13, 0x00, 0x2b, 0x05, 0x12, 0x02, 0x2a, 0x01, 0x04, 0x00,
        0x35, 0x0b, 0x11, 0x03, 0x29, 0x0a, 0x10, 0x00, 0x28, 0x09, 0x0f, 0x02, 0x27, 0x01, 0x08, 0x00,
        0x34, 0x07, 0x0e, 0x03, 0x26, 0x06, 0x0d, 0x00, 0x25, 0x05, 0x0c, 0x02, 0x24, 0x01, 0x04, 0x00,
        0x33, 0x0b, 0x17, 0x03, 0x23, 0x0a, 0x16, 0x00, 0x22, 0x09, 0x15, 0x02, 0x21, 0x01, 0x08, 0x00,
        0x32, 0x07, 0x14, 0x03, 0x20, 0x06, 0x13, 0x00, 0x1f, 0x05, 0x12, 0x02, 0x1e, 0x01, 0x04, 0x00,
        0x31, 0x0b, 0x11, 0x03, 0x1d, 0x0a, 0x10, 0x00, 0x1c, 0x09, 0x0f, 0x02, 0x1b, 0x01, 0x08, 0x00,
        0x30, 0x07, 0x0e, 0x03, 0x1a, 0x06, 0x0d, 0x00, 0x19, 0x05, 0x0c, 0x02, 0x18, 0x01, 0x04, 0x00,
    ])
    yj2_data2 = bytes([
        0x08, 0x05, 0x06, 0x04, 0x07, 0x05, 0x06, 0x03, 0x07, 0x05, 0x06, 0x04, 0x07, 0x04, 0x05, 0x03,
    ])

    if data is None or len(data) < 4:
        return None

    length = struct.unpack_from('<I', data, 0)[0]
    src = data[4:]
    dest = bytearray()

    # 构建自适应 Huffman 树
    # node: [weight, value, parent_idx, left_idx, right_idx]
    NODE_W, NODE_V, NODE_P, NODE_L, NODE_R = 0, 1, 2, 3, 4
    num_nodes = 641
    nodes = [[0, 0, 0, 0, 0] for _ in range(num_nodes)]
    node_list = [0] * 321  # value -> node index mapping

    for i in range(0x141):
        node_list[i] = i
    for i in range(0x281):
        nodes[i][NODE_V] = i
        nodes[i][NODE_W] = 1

    nodes[0x280][NODE_P] = 0x280

    ptr = 0x141
    for i in range(0, 0x280, 2):
        nodes[ptr][NODE_L] = i
        nodes[ptr][NODE_R] = i + 1
        nodes[i][NODE_P] = ptr
        nodes[i + 1][NODE_P] = ptr
        nodes[ptr][NODE_W] = nodes[i][NODE_W] + nodes[i + 1][NODE_W]
        ptr += 1

    def yj2_bt(pos):
        byte_idx = pos >> 3
        if byte_idx >= len(src):
            return 0
        return (src[byte_idx] & (1 << (pos & 0x7))) >> (pos & 0x7)

    def yj2_adjust_tree(value):
        ni = node_list[value]
        while nodes[ni][NODE_V] != 0x280:
            ti = ni + 1
            while ti < num_nodes and nodes[ni][NODE_W] == nodes[ti][NODE_W]:
                ti += 1
            ti -= 1
            if ti != ni:
                # swap parent
                tmp_p = nodes[ni][NODE_P]
                nodes[ni][NODE_P] = nodes[ti][NODE_P]
                nodes[ti][NODE_P] = tmp_p

                if nodes[ni][NODE_V] > 0x140:
                    nodes[nodes[ni][NODE_L]][NODE_P] = ti
                    nodes[nodes[ni][NODE_R]][NODE_P] = ti
                else:
                    node_list[nodes[ni][NODE_V]] = ti

                if nodes[ti][NODE_V] > 0x140:
                    nodes[nodes[ti][NODE_L]][NODE_P] = ni
                    nodes[nodes[ti][NODE_R]][NODE_P] = ni
                else:
                    node_list[nodes[ti][NODE_V]] = ni

                # swap nodes
                nodes[ni], nodes[ti] = nodes[ti], nodes[ni]
                ni = ti

            nodes[ni][NODE_W] += 1
            ni = nodes[ni][NODE_P]
        nodes[ni][NODE_W] += 1

    bit_ptr = 0

    while True:
        ni = 0x280
        while nodes[ni][NODE_V] > 0x140:
            if yj2_bt(bit_ptr):
                ni = nodes[ni][NODE_R]
            else:
                ni = nodes[ni][NODE_L]
            bit_ptr += 1

        val = nodes[ni][NODE_V]

        if nodes[0x280][NODE_W] == 0x8000:
            for i in range(0x141):
                if nodes[node_list[i]][NODE_W] & 0x1:
                    yj2_adjust_tree(i)
            for i in range(0x281):
                nodes[i][NODE_W] >>= 1

        yj2_adjust_tree(val)

        if val > 0xff:
            # LZ 回溯引用
            temp = 0
            for i in range(8):
                temp |= yj2_bt(bit_ptr) << i
                bit_ptr += 1

            tmp = temp & 0xff
            extra_bits = yj2_data2[tmp & 0xf] + 6
            for i in range(8, extra_bits):
                temp |= yj2_bt(bit_ptr) << i
                bit_ptr += 1

            temp >>= yj2_data2[tmp & 0xf]
            pos = (temp & 0x3f) | (yj2_data1[tmp] << 6)

            if pos == 0xfff:
                break

            copy_len = val - 0xfd
            start = len(dest) - pos - 1
            for i in range(copy_len):
                if start + i >= 0 and start + i < len(dest):
                    dest.append(dest[start + i])
                else:
                    dest.append(0)
        else:
            dest.append(val)

    return bytes(dest[:length])


# ============================================================
# 调色板读取
# ============================================================

def load_palette(pat_mkf_path, palette_idx=0, night=False):
    """从 pat.mkf 读取 256 色调色板（6-bit → 8-bit）"""
    mkf = MKFReader(pat_mkf_path)
    raw = mkf.get_chunk_raw(palette_idx)
    if raw is None:
        return None

    palette = []
    offset = 256 * 3 if (night and len(raw) > 256 * 3) else 0

    for i in range(256):
        r = (raw[offset + i * 3] & 0x3f) << 2
        g = (raw[offset + i * 3 + 1] & 0x3f) << 2
        b = (raw[offset + i * 3 + 2] & 0x3f) << 2
        palette.append((r, g, b))

    return palette


# ============================================================
# FBP（全屏背景图）提取
# ============================================================

def extract_fbp(fbp_mkf_path, chunk_idx, palette):
    """提取一张 320x200 FBP 全屏背景图"""
    mkf = MKFReader(fbp_mkf_path)
    pixel_data = mkf.get_chunk_decompressed(chunk_idx)
    if pixel_data is None or len(pixel_data) < 320 * 200:
        return None

    pixels = []
    for i in range(320 * 200):
        idx = pixel_data[i]
        pixels.append(palette[idx])

    return pixels


# ============================================================
# 放大算法
# ============================================================

class SimpleCanvas:
    """简单画布封装"""
    def __init__(self, w, h, pixels):
        self.w = w
        self.h = h
        self.pixels = pixels

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.pixels[y * self.w + x]
        # 边界钳制
        x = max(0, min(x, self.w - 1))
        y = max(0, min(y, self.h - 1))
        return self.pixels[y * self.w + x]


def scale_nearest(canvas, factor):
    """最近邻放大"""
    nw, nh = canvas.w * factor, canvas.h * factor
    out = [(0, 0, 0)] * (nw * nh)
    for y in range(nh):
        sy = y // factor
        row = sy * canvas.w
        out_row = y * nw
        for x in range(nw):
            out[out_row + x] = canvas.pixels[row + x // factor]
    return out, nw, nh


def scale_bilinear(canvas, factor):
    """双线性插值"""
    nw, nh = canvas.w * factor, canvas.h * factor
    out = [(0, 0, 0)] * (nw * nh)
    for y in range(nh):
        sy = y / factor
        y0 = min(int(sy), canvas.h - 1)
        y1 = min(y0 + 1, canvas.h - 1)
        fy = sy - y0
        fy1 = 1.0 - fy
        for x in range(nw):
            sx = x / factor
            x0 = min(int(sx), canvas.w - 1)
            x1 = min(x0 + 1, canvas.w - 1)
            fx = sx - x0
            fx1 = 1.0 - fx
            c00 = canvas.pixels[y0 * canvas.w + x0]
            c10 = canvas.pixels[y0 * canvas.w + x1]
            c01 = canvas.pixels[y1 * canvas.w + x0]
            c11 = canvas.pixels[y1 * canvas.w + x1]
            w00, w10, w01, w11 = fx1 * fy1, fx * fy1, fx1 * fy, fx * fy
            r = int(c00[0] * w00 + c10[0] * w10 + c01[0] * w01 + c11[0] * w11)
            g = int(c00[1] * w00 + c10[1] * w10 + c01[1] * w01 + c11[1] * w11)
            b = int(c00[2] * w00 + c10[2] * w10 + c01[2] * w01 + c11[2] * w11)
            out[y * nw + x] = (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
    return out, nw, nh


def color_dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])


def mix_color(a, b, t):
    return (
        int(a[0] * (1 - t) + b[0] * t),
        int(a[1] * (1 - t) + b[1] * t),
        int(a[2] * (1 - t) + b[2] * t),
    )


def scale_xbr_style(canvas, factor):
    """简化版 xBR/xBRZ 风格边缘感知放大"""
    nw, nh = canvas.w * factor, canvas.h * factor
    out = [(0, 0, 0)] * (nw * nh)
    threshold = 48
    total = canvas.h

    for y in range(canvas.h):
        if y % max(1, total // 10) == 0:
            print(f"    xBR: {y}/{total}", flush=True)
        for x in range(canvas.w):
            c = canvas.get(x, y)
            n = {
                'N': canvas.get(x, y - 1), 'S': canvas.get(x, y + 1),
                'W': canvas.get(x - 1, y), 'E': canvas.get(x + 1, y),
                'NW': canvas.get(x - 1, y - 1), 'NE': canvas.get(x + 1, y - 1),
                'SW': canvas.get(x - 1, y + 1), 'SE': canvas.get(x + 1, y + 1),
            }

            for fy in range(factor):
                for fx in range(factor):
                    ox, oy = x * factor + fx, y * factor + fy
                    px = (fx + 0.5) / factor
                    py = (fy + 0.5) / factor
                    result = c

                    if color_dist(n['NW'], c) < threshold and color_dist(n['SE'], c) < threshold:
                        if color_dist(n['NE'], c) > threshold and color_dist(n['SW'], c) > threshold:
                            if px + py < 1.0:
                                blend = max(0, 1.0 - (px + py))
                                if color_dist(n['N'], c) < threshold:
                                    result = mix_color(c, n['N'], blend * 0.5)
                                elif color_dist(n['W'], c) < threshold:
                                    result = mix_color(c, n['W'], blend * 0.5)
                            else:
                                blend = max(0, (px + py) - 1.0)
                                if color_dist(n['S'], c) < threshold:
                                    result = mix_color(c, n['S'], blend * 0.5)
                                elif color_dist(n['E'], c) < threshold:
                                    result = mix_color(c, n['E'], blend * 0.5)
                    elif color_dist(n['NE'], c) < threshold and color_dist(n['SW'], c) < threshold:
                        if color_dist(n['NW'], c) > threshold and color_dist(n['SE'], c) > threshold:
                            if (1 - px) + py < 1.0:
                                blend = max(0, 1.0 - ((1 - px) + py))
                                if color_dist(n['N'], c) < threshold:
                                    result = mix_color(c, n['N'], blend * 0.5)
                                elif color_dist(n['E'], c) < threshold:
                                    result = mix_color(c, n['E'], blend * 0.5)
                            else:
                                blend = max(0, ((1 - px) + py) - 1.0)
                                if color_dist(n['S'], c) < threshold:
                                    result = mix_color(c, n['S'], blend * 0.5)
                                elif color_dist(n['W'], c) < threshold:
                                    result = mix_color(c, n['W'], blend * 0.5)
                    else:
                        blend_r, blend_g, blend_b = float(c[0]), float(c[1]), float(c[2])
                        weight = 0.0
                        for nc in [n['N'], n['S'], n['E'], n['W']]:
                            d = color_dist(nc, c)
                            if d < threshold:
                                w = 0.08
                                blend_r += nc[0] * w
                                blend_g += nc[1] * w
                                blend_b += nc[2] * w
                                weight += w
                        if weight > 0:
                            total_w = 1 + weight
                            result = (
                                max(0, min(255, int(blend_r / total_w))),
                                max(0, min(255, int(blend_g / total_w))),
                                max(0, min(255, int(blend_b / total_w))),
                            )

                    out[oy * nw + ox] = result

    return out, nw, nh


# ============================================================
# 标签生成
# ============================================================

def create_label_pixels(text, width, color=(255, 255, 255)):
    """用像素字母生成标签"""
    FONT = {
        'O': ["01110","10001","10001","10001","10001","10001","01110"],
        'R': ["11110","10001","10001","11110","10100","10010","10001"],
        'I': ["11111","00100","00100","00100","00100","00100","11111"],
        'G': ["01110","10001","10000","10111","10001","10001","01110"],
        'N': ["10001","11001","10101","10101","10011","10001","10001"],
        'A': ["01110","10001","10001","11111","10001","10001","10001"],
        'L': ["10000","10000","10000","10000","10000","10000","11111"],
        'E': ["11111","10000","10000","11110","10000","10000","11111"],
        'S': ["01111","10000","10000","01110","00001","00001","11110"],
        'T': ["11111","00100","00100","00100","00100","00100","00100"],
        'B': ["11110","10001","10001","11110","10001","10001","11110"],
        'X': ["10001","01010","00100","00100","00100","01010","10001"],
        'Z': ["11111","00001","00010","00100","01000","10000","11111"],
        '-': ["00000","00000","00000","11111","00000","00000","00000"],
        'D': ["11100","10010","10001","10001","10001","10010","11100"],
        'H': ["10001","10001","10001","11111","10001","10001","10001"],
        '(': ["00100","01000","10000","10000","10000","01000","00100"],
        ')': ["00100","00010","00001","00001","00001","00010","00100"],
        ' ': ["00000","00000","00000","00000","00000","00000","00000"],
        'x': ["00000","00000","10001","01010","00100","01010","10001"],
        'F': ["11111","10000","10000","11110","10000","10000","10000"],
        'C': ["01110","10001","10000","10000","10000","10001","01110"],
        'K': ["10001","10010","10100","11000","10100","10010","10001"],
        'P': ["11110","10001","10001","11110","10000","10000","10000"],
        'W': ["10001","10001","10001","10101","10101","10101","01010"],
        'Y': ["10001","01010","00100","00100","00100","00100","00100"],
        'U': ["10001","10001","10001","10001","10001","10001","01110"],
        'V': ["10001","10001","10001","01010","01010","00100","00100"],
        '#': ["01010","11111","01010","01010","11111","01010","00000"],
        '0': ["01110","10001","10011","10101","11001","10001","01110"],
        '1': ["00100","01100","00100","00100","00100","00100","01110"],
        '2': ["01110","10001","00001","00010","00100","01000","11111"],
        '3': ["11110","00001","00001","01110","00001","00001","11110"],
        '4': ["10001","10001","10001","11111","00001","00001","00001"],
    }
    label_h = 24
    pixels = [(20, 18, 25)] * (width * label_h)
    scale = 2
    text = text.upper()
    total_w = len(text) * 6 * scale
    start_x = (width - total_w) // 2
    start_y = (label_h - 7 * scale) // 2

    for ci, ch in enumerate(text):
        glyph = FONT.get(ch, FONT[' '])
        for gy in range(7):
            for gx in range(5):
                if glyph[gy][gx] == '1':
                    for sy in range(scale):
                        for sx in range(scale):
                            px_x = start_x + ci * 6 * scale + gx * scale + sx
                            py_y = start_y + gy * scale + sy
                            if 0 <= px_x < width and 0 <= py_y < label_h:
                                pixels[py_y * width + px_x] = color
    return pixels, label_h


# ============================================================
# 拼接对比图
# ============================================================

def stitch_comparison(canvas, factor):
    """生成四列对比图: Original(1:1居中) | Nearest | Bilinear | xBR-Edge"""
    sw, sh = canvas.w * factor, canvas.h * factor
    print(f"  原始: {canvas.w}x{canvas.h} → 放大到: {sw}x{sh}")

    # 构建 Original 列：1:1 原图居中放在 sw x sh 的黑底画布上
    print("  [1/4] Original (1:1 原始像素)...")
    original_px = [(10, 8, 15)] * (sw * sh)
    ox_off = (sw - canvas.w) // 2
    oy_off = (sh - canvas.h) // 2
    for y in range(canvas.h):
        for x in range(canvas.w):
            px = ox_off + x
            py = oy_off + y
            if 0 <= px < sw and 0 <= py < sh:
                original_px[py * sw + px] = canvas.pixels[y * canvas.w + x]
    # 画一个白色细边框标出原图边界
    border_color = (80, 80, 80)
    bx0, by0 = ox_off - 1, oy_off - 1
    bx1, by1 = ox_off + canvas.w, oy_off + canvas.h
    for x in range(max(0, bx0), min(sw, bx1 + 1)):
        if 0 <= by0 < sh:
            original_px[by0 * sw + x] = border_color
        if 0 <= by1 < sh:
            original_px[by1 * sw + x] = border_color
    for y in range(max(0, by0), min(sh, by1 + 1)):
        if 0 <= bx0 < sw:
            original_px[y * sw + bx0] = border_color
        if 0 <= bx1 < sw:
            original_px[y * sw + bx1] = border_color

    print("  [2/4] Nearest Neighbor...")
    nearest_px, _, _ = scale_nearest(canvas, factor)

    print("  [3/4] Bilinear...")
    bilinear_px, _, _ = scale_bilinear(canvas, factor)

    print("  [4/4] xBR-Edge (类似 ScaleFX)...")
    xbr_px, _, _ = scale_xbr_style(canvas, factor)

    gap = 4
    cols = 4
    total_w = sw * cols + gap * (cols - 1)
    label0_px, label_h = create_label_pixels("Original (1x)", sw, (255, 200, 100))
    label1_px, _ = create_label_pixels(f"Nearest ({factor}x)", sw, (200, 200, 200))
    label2_px, _ = create_label_pixels(f"Bilinear ({factor}x)", sw, (200, 200, 200))
    label3_px, _ = create_label_pixels(f"xBR-Edge ({factor}x)", sw, (100, 255, 100))

    total_h = label_h + sh
    out = [(20, 18, 25)] * (total_w * total_h)

    # 标签行
    label_list = [label0_px, label1_px, label2_px, label3_px]
    for col_i in range(cols):
        col_offset = col_i * (sw + gap)
        for y in range(label_h):
            for x in range(sw):
                out[y * total_w + col_offset + x] = label_list[col_i][y * sw + x]

    # 图像行
    img_list = [original_px, nearest_px, bilinear_px, xbr_px]
    for col_i in range(cols):
        col_offset = col_i * (sw + gap)
        for y in range(sh):
            oy = label_h + y
            for x in range(sw):
                out[oy * total_w + col_offset + x] = img_list[col_i][y * sw + x]

    # 分隔线
    for y in range(total_h):
        for col_i in range(1, cols):
            gap_start = col_i * sw + (col_i - 1) * gap
            for g in range(gap):
                out[y * total_w + gap_start + g] = (40, 35, 50)

    return out, total_w, total_h


def crop_canvas(canvas, x, y, w, h):
    """裁剪画布局部区域"""
    pixels = []
    for dy in range(h):
        for dx in range(w):
            pixels.append(canvas.get(x + dx, y + dy))
    return SimpleCanvas(w, h, pixels)


# ============================================================
# 主函数
# ============================================================

def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    game_dir = "/Users/daniel/projects/owner/PalOpen/仙剑奇侠传98柔情版(正版)"

    fbp_path = os.path.join(game_dir, "Fbp.mkf")
    pat_path = os.path.join(game_dir, "Pat.mkf")

    if not os.path.exists(fbp_path) or not os.path.exists(pat_path):
        print(f"错误: 找不到游戏文件")
        print(f"  Fbp.mkf: {fbp_path}")
        print(f"  Pat.mkf: {pat_path}")
        sys.exit(1)

    print("=" * 60)
    print("  仙剑高清方案 — 真实游戏素材 Shader 放大效果对比")
    print("=" * 60)

    # 加载调色板（使用第 0 号调色板）
    print("\n加载调色板 (Pat.mkf, palette #0)...")
    palette = load_palette(pat_path, 0)
    if palette is None:
        print("错误: 无法加载调色板")
        sys.exit(1)
    print(f"  调色板加载成功: 256 色")

    # 查看 FBP 文件有多少张图
    fbp_mkf = MKFReader(fbp_path)
    fbp_count = fbp_mkf.get_chunk_count()
    print(f"\nFbp.mkf 包含 {fbp_count} 张全屏背景图")

    # 手动选择最具代表性的 FBP 场景
    # #60=李逍遥 #62=赵灵儿 #66=林月如 #2=竹简葫芦 #75=海浪
    target_chunks = [60, 62, 66]
    selected = []
    for i in target_chunks:
        try:
            pixels = extract_fbp(fbp_path, i, palette)
            if pixels is not None:
                selected.append((i, pixels))
        except Exception as e:
            print(f"  跳过 FBP #{i}: {e}")
            continue

    if not selected:
        print("错误: 无法提取任何有效的 FBP 图片")
        sys.exit(1)

    print(f"\n已选择 {len(selected)} 张 FBP 图片: {[s[0] for s in selected]}")

    for idx, (chunk_idx, pixels) in enumerate(selected):
        print(f"\n{'=' * 60}")
        print(f"  处理第 {idx+1} 张 FBP (chunk #{chunk_idx})")
        print(f"{'=' * 60}")

        # 保存原始图
        orig_path = os.path.join(out_dir, f"real_fbp_{chunk_idx}_original.png")
        write_png(orig_path, pixels, 320, 200)

        canvas = SimpleCanvas(320, 200, pixels)

        # 全景 2x 对比
        print(f"\n生成全景 2x 放大对比...")
        comp_px, comp_w, comp_h = stitch_comparison(canvas, 2)
        full_path = os.path.join(out_dir, f"real_fbp_{chunk_idx}_compare_2x.png")
        write_png(full_path, comp_px, comp_w, comp_h)

        # 局部特写 4x — 根据内容选择裁剪区域
        # FBP #60 李逍遥: 脸部区域大约在 (50, 30, 120, 100)
        # FBP #62 赵灵儿: 脸部区域大约在 (80, 20, 120, 90)
        # FBP #66 林月如: 脸部区域大约在 (100, 10, 120, 90)
        crop_regions = {
            60: (50, 30, 80, 60),    # 李逍遥脸部+上半身
            62: (80, 15, 80, 60),    # 赵灵儿脸部
            66: (100, 10, 80, 60),   # 林月如脸部
        }
        cx, cy, cw, ch = crop_regions.get(chunk_idx, (100, 40, 80, 60))

        print(f"\n生成人物特写 4x 放大对比 (区域: {cx},{cy} {cw}x{ch})...")
        crop = crop_canvas(canvas, cx, cy, cw, ch)
        crop_px, crop_w, crop_h = stitch_comparison(crop, 4)
        crop_path = os.path.join(out_dir, f"real_fbp_{chunk_idx}_detail_4x.png")
        write_png(crop_path, crop_px, crop_w, crop_h)

    print(f"\n{'=' * 60}")
    print("  所有对比图已生成！")
    print(f"  输出目录: {out_dir}")
    print(f"{'=' * 60}")
    print("\n对比说明:")
    print("  Nearest  — 像素块直接放大，锯齿明显（最原始）")
    print("  Bilinear — 双线性插值，平滑但模糊（丢失细节）")
    print("  xBR-Edge — 边缘感知智能放大（类似 ScaleFX/xBRZ shader 效果）")
    print("             ↑ 这就是 PLAN.md 中推荐的 GLSL shader 方案的原理")
    print("\n注意: Python CPU 实现的 xBR 只是简化版。")
    print("真正的 GPU ScaleFX shader 用 4-5 pass 做更复杂的边缘分析，效果更好。")


if __name__ == '__main__':
    main()
