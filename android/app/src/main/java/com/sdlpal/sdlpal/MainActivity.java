/* -*- mode: c; tab-width: 4; c-basic-offset: 4; c-file-style: "linux" -*- */
//
// Copyright (c) 2009-2011, Wei Mingzhi <whistler_wmz@users.sf.net>.
// Copyright (c) 2011-2024, SDLPAL development team.
// All rights reserved.
//
// This file is part of SDLPAL.
//
// SDLPAL is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License version 3
// as published by the Free Software Foundation.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.
//

package com.sdlpal.sdlpal;

import android.Manifest;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.Context;
import android.content.pm.PackageManager;
import android.os.*;
import androidx.annotation.NonNull;
import android.app.Activity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import android.provider.Settings;
import android.net.Uri;
import android.util.Log;
import android.provider.DocumentsContract;
import android.content.ContentResolver;
import androidx.documentfile.provider.DocumentFile;
import androidx.activity.result.*;
import androidx.activity.result.contract.*;

import java.io.*;
import android.content.res.AssetManager;

public class MainActivity extends AppCompatActivity {

    static {
        System.loadLibrary("SDL3");
        System.loadLibrary("main");
    }

    private static MainActivity mSingleton;
    private ActivityResultLauncher<Intent> permissionRequestLauncher;

    private static final String TAG = "sdlpal-debug";

    private static Uri docTreeUri = null;
    private static String docUri = null;
    private static String basePath = "";
    private static String dataPath = "";
    private static String cachePath = "";

    public static String getBasePath() {
        return basePath;
    }

    private static void setBasePath(String basepath) {
        SetAppPath(basepath, dataPath, cachePath);
    }

    public static native void setAppPath(String basepath, String datapath, String cachepath);
    public static void SetAppPath(String basepath, String datapath, String cachepath)
    {
        basePath = basepath;
        dataPath = datapath;
        cachePath = cachepath;
        setAppPath(basePath, dataPath, cachePath);
    }

    public static boolean crashed = false;
    public static boolean blocked = false;

    private final AppCompatActivity mActivity = this;

    interface RequestForPermissions {
        void request();
    }

    private void alertUser(int id, final RequestForPermissions req) {
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setMessage(id);
        builder.setCancelable(false);
        builder.setPositiveButton(android.R.string.ok, new DialogInterface.OnClickListener() {
            @Override
            public void onClick(DialogInterface dialogInterface, int i) {
                req.request();
            }
        });
        builder.setNegativeButton(android.R.string.cancel, new DialogInterface.OnClickListener() {
            @Override
            public void onClick(DialogInterface dialogInterface, int i) {
                System.exit(1);
            }
        });
        builder.create().show();
    }

    private static int getFileDescriptorFromUri(Uri data, String mode) {
        try {
            ContentResolver cr = mSingleton.getApplicationContext().getContentResolver();
            ParcelFileDescriptor inputPFD = cr.openFileDescriptor(data, mode);
            if (inputPFD == null) {
                Log.e(TAG, "getFileDescriptorFromUri: Failed to get parcel file descriptor ");
                return -1;
            }
            return inputPFD.detachFd();
        } catch (Exception e) {
            Log.w(TAG, "getFileDescriptorFromUri:" + e.toString());
        }
        return -1;
    }

    public static Uri getDocumentUriFromPath(String path) {
        try {
            if(basePath.isEmpty())
                throw new Exception("basePath is empty");
            Context ctx = mSingleton.getApplicationContext();
            path = path.replace(basePath, "");
            path = path.replace("/","%2F");
            String pathUri = docUri + "%2F" + path;
            pathUri = pathUri.replace("%2F%2F","%2F");
            String documentId = DocumentsContract.getDocumentId(Uri.parse(pathUri));
            Uri documentUri = DocumentsContract.buildDocumentUriUsingTree(docTreeUri, documentId);
            return documentUri;
        } catch (Exception e) {
            Log.w(TAG, "Exception: getDocumentUriFromPath:" + e.toString());
        }
        return null;
    }

    public static boolean isExternalStorageDocument(Uri uri) {
        return "com.android.externalstorage.documents".equals(uri.getAuthority());
    }

    public static String getPath(final Uri uri) {
        Context context = mSingleton.getApplicationContext();
        // DocumentProvider
        if (DocumentsContract.isTreeUri(uri)) {
            if (isExternalStorageDocument(uri)) {
                final String docId = DocumentsContract.getTreeDocumentId(uri);
                final String[] split = docId.split(":");
                final String type = split[0];
                if ("primary".equalsIgnoreCase(type)) {
                    return Environment.getExternalStorageDirectory() + "/" + split[1];
                }else{
                    return Environment.getExternalStorageDirectory().getPath().replace("emulated/0",type) + "/" + split[1];
                }
            }
        }else
        if (DocumentsContract.isDocumentUri(context, uri)) {
            // ExternalStorageProvider
            if (isExternalStorageDocument(uri)) {
                final String docId = DocumentsContract.getDocumentId(uri);
                final String[] split = docId.split(":");
                final String type = split[0];

                if ("primary".equalsIgnoreCase(type)) {
                    return Environment.getExternalStorageDirectory() + "/" + split[1];
                }else{
                    return Environment.getExternalStorageDirectory().getPath().replace("emulated/0",type) + "/" + split[1];
                }
            }
        }

        return "";
    }

    public static int SAF_access(String path, int mode) {
        if( path.startsWith("/data/") ) {
            File file = new File(path);
            return file.exists() ? 0 : -1;
        }
        return getFileDescriptorFromUri(getDocumentUriFromPath(path), "r") != -1 ? 0 : -1;
    }

    public static int SAF_fopen(String path, String mode) {
        Context context = mSingleton.getApplicationContext();
        Uri uri = getDocumentUriFromPath(path);
        mode = mode.substring(0,1);
        try {
            File file = new File(path);
            DocumentFile documentFile = DocumentFile.fromSingleUri(context, uri);
            if( mode.equals("w") && documentFile != null && !documentFile.exists() ) {
                if( path.startsWith("/data") ) {
                    file.createNewFile();
                    file.setReadable(true);
                    file.setWritable(true);
                }else if( path.startsWith("/storage") ) {
                    DocumentFile baseDocument = DocumentFile.fromTreeUri(context, docTreeUri);
                    if (documentFile != null) {
                        DocumentFile newFile = baseDocument.createFile("application/octet-stream", file.getName());
                        if (newFile != null) {
                            uri = newFile.getUri();
                        } 
                    }
                }
            }
            if(path.startsWith("/data"))
                uri = Uri.fromFile( file );
        }catch (Exception e) {
            Log.w(TAG, "Exception: SAF_fopen create file for writing:" + e.toString());
        }
        return getFileDescriptorFromUri(uri, mode);
    }

    protected static void setPersistedUri(Uri uri, boolean save) {
        try{
            if (uri != null) {
                docTreeUri = uri;
                docUri = uri.toString().replace("tree", "document");
                String filePath = getPath(uri);
                setBasePath(filePath);
                if(save)
                    savePersistedUriToCache();
            }
        }catch(Exception e) {
            Log.v(TAG,"setPersistedUri exception:" + e.toString());
        }
    }
    public static void setPersistedUri(Uri uri) {
        setPersistedUri(uri, true);
    }

    public static Uri getDocTreeUri() {
        return docTreeUri;
    }

    protected void loadPersistedUriFromCache() {
        File persistFile = new File(cachePath + "/persisted");
        FileInputStream in;
        try {
            int length = (int) persistFile.length();
            byte[] bytes = new byte[length];
            in = new FileInputStream(persistFile);
            in.read(bytes);
            String contents = new String(bytes);
            Uri uri = Uri.parse(contents);
            setPersistedUri(uri, false); 
            in.close();
            basePath = getPath(uri);
        }catch(FileNotFoundException e) {
            blocked = true;
            alertUser(R.string.toast_requestpermission, new RequestForPermissions() {
                                                            @Override
                                                            public void request() {
                                                                Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
                                                                i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
                                                                mSingleton.permissionRequestLauncher.launch(i);
                                                            }
                                                        });
        }catch(Exception e) {
            Log.w(TAG, "Exception: loadPersistedUriFromCache:"+e.toString());
        }
    }

    protected static void savePersistedUriToCache() {
        if (docTreeUri != null) {
            File persistFile = new File(cachePath + "/persisted");
            FileOutputStream out;
            try {
                out = new FileOutputStream(persistFile);
                out.write(docTreeUri.toString().getBytes());
                out.close();
            } catch(Exception e) {
                Log.w(TAG, "Exception: savePersistedUriToCache:"+e.toString());
            }
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        mSingleton = this;
        permissionRequestLauncher = registerForActivityResult(
        new ActivityResultContracts.StartActivityForResult(),
        new ActivityResultCallback<ActivityResult>() {
            @Override
            public void onActivityResult(ActivityResult result) {
                if (result.getResultCode() == Activity.RESULT_OK) {
                    Intent data = result.getData();
                    Uri uri = data.getData();
                    getContentResolver().takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
                    setPersistedUri(uri);
                    StartGame();
                }
            }
        });
    }

    private boolean hasBuiltinAssets() {
        try {
            String[] files = getAssets().list("gamedata");
            return files != null && files.length > 0;
        } catch (IOException e) {
            return false;
        }
    }

    private String getBuiltinGamePath() {
        return getApplicationContext().getFilesDir().getPath() + "/gamedata";
    }

    private void extractAssets() {
        String destPath = getBuiltinGamePath();
        File destDir = new File(destPath);
        File marker = new File(destPath + "/.extracted");
        if (marker.exists()) return;

        destDir.mkdirs();

        try {
            AssetManager am = getAssets();
            // 递归复制 gamedata/ 下的所有文件和子目录
            copyAssetDir(am, "gamedata", destPath);
            marker.createNewFile();
            Log.i(TAG, "Assets extracted to " + destPath);
        } catch (IOException e) {
            Log.e(TAG, "Failed to extract assets", e);
        }
    }

    private void copyAssetDir(AssetManager am, String assetDir, String destDir) throws IOException {
        String[] entries = am.list(assetDir);
        if (entries == null) return;
        new File(destDir).mkdirs();
        for (String entry : entries) {
            String assetPath = assetDir + "/" + entry;
            String destPath = destDir + "/" + entry;
            // 尝试列出子条目，如果非空则为目录
            String[] sub = am.list(assetPath);
            if (sub != null && sub.length > 0) {
                copyAssetDir(am, assetPath, destPath);
            } else {
                copyAssetFile(am, assetPath, destPath);
            }
        }
    }

    private void copyAssetFile(AssetManager am, String assetPath, String destPath) throws IOException {
        InputStream in = am.open(assetPath);
        FileOutputStream out = new FileOutputStream(destPath);
        byte[] buf = new byte[65536];
        int len;
        while ((len = in.read(buf)) > 0) {
            out.write(buf, 0, len);
        }
        out.close();
        in.close();
    }

    private void writeDefaultConfig(String gamePath) {
        File cfgFile = new File(gamePath + "/sdlpal.cfg");
        if (cfgFile.exists()) return;
        try {
            FileOutputStream out = new FileOutputStream(cfgFile);
            String cfg = "KeepAspectRatio=1\n" +
                "FullScreen=0\n" +
                "LaunchSetting=1\n" +
                "Stereo=1\n" +
                "UseSurroundOPL=1\n" +
                "EnableKeyRepeat=0\n" +
                "UseTouchOverlay=1\n" +
                "EnableAviPlay=1\n" +
                "EnableGLSL=1\n" +
                "EnableHDR=1\n" +
                "SurroundOPLOffset=384\n" +
                "LogLevel=0\n" +
                "AudioDevice=-1\n" +
                "AudioBufferSize=1024\n" +
                "OPLSampleRate=49716\n" +
                "ResampleQuality=4\n" +
                "SampleRate=48000\n" +
                "MusicVolume=100\n" +
                "SoundVolume=100\n" +
                "WindowHeight=400\n" +
                "WindowWidth=640\n" +
                "TextureHeight=1200\n" +
                "TextureWidth=1920\n" +
                "CD=NONE\n" +
                "Music=RIX\n" +
                "MIDISynth=native\n" +
                "OPLCore=DBFLT\n" +
                "OPLChip=OPL2\n" +
                "Shader=scalefx.glslp\n" +
                "GamePath=" + gamePath + "\n" +
                "SavePath=" + gamePath + "\n" +
                "ShaderPath=" + gamePath + "\n";
            out.write(cfg.getBytes());
            out.close();
            Log.i(TAG, "Default config written to " + cfgFile.getPath());
        } catch (IOException e) {
            Log.e(TAG, "Failed to write default config", e);
        }
    }

    public void onStart() {
        super.onStart();
        cachePath = getApplicationContext().getCacheDir().getPath();
        String dataPath = getApplicationContext().getFilesDir().getPath();

        if (hasBuiltinAssets()) {
            // 内置资源模式：解压 assets 到私有目录，跳过 SAF
            extractAssets();
            String gamePath = getBuiltinGamePath();
            writeDefaultConfig(gamePath);
            SetAppPath(gamePath, dataPath, cachePath);
            basePath = gamePath;
        } else {
            // 外部资源模式：走原有 SAF 流程
            loadPersistedUriFromCache();
            String sdlpalPath = basePath;
            if (SettingsActivity.loadConfigFile()) {
                String gamePath = SettingsActivity.getConfigString(SettingsActivity.GamePath, true);
                if (gamePath != null && !gamePath.isEmpty())
                    sdlpalPath = gamePath;
            }
            SetAppPath(sdlpalPath, dataPath, cachePath);
        }

        if (!blocked)
            StartGame();
    }


    public void StartGame() {
        File runningFile = new File(cachePath + "/running");
        crashed = runningFile.exists();

        Intent intent;
        if (SettingsActivity.loadConfigFile() || crashed) {
            runningFile.delete();

            intent = new Intent(this, SettingsActivity.class);
        } else {
            intent = new Intent(this, PalActivity.class);
        }
        intent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP);
        startActivity(intent);
        finish();
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
    }
}
