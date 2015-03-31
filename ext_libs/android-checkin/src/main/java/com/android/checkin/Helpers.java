package com.android.checkin;

import java.io.IOException;
import java.io.InputStream;
import java.util.zip.GZIPOutputStream;
import java.io.ByteArrayOutputStream;

public class Helpers {
    public static byte[] inputStreamToBytes(InputStream inputStream) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        byte[] buffer = new byte[2048];
        int read = 0;
        while ((read = inputStream.read(buffer, 0, buffer.length)) != -1)
            baos.write(buffer, 0, read);
        baos.flush();
        return baos.toByteArray();
    }
}
