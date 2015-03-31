package com.android.checkin;

import java.io.IOException;
import java.io.InputStream;
import java.util.zip.GZIPOutputStream;
import java.io.ByteArrayOutputStream;

import org.apache.http.impl.client.DefaultHttpClient;
import org.apache.http.impl.client.EntityEnclosingRequestWrapper;
import org.apache.http.client.entity.GzipDecompressingEntity;
import org.apache.http.entity.ByteArrayEntity;
import org.apache.http.protocol.HttpContext;
import org.apache.http.HttpRequestInterceptor;
import org.apache.http.HttpResponseInterceptor;
import org.apache.http.HttpRequest;
import org.apache.http.HttpResponse;
import org.apache.http.HttpException;
import org.apache.http.HttpEntity;
import org.apache.http.Header;
import org.apache.http.HeaderElement;

public class HttpClientGzip extends DefaultHttpClient {
    public HttpClientGzip() {
        super();

        addRequestInterceptor(new HttpRequestInterceptor() {
            public void process(final HttpRequest request, final HttpContext context) throws HttpException, IOException {
                if (request instanceof EntityEnclosingRequestWrapper) {
                    EntityEnclosingRequestWrapper post = (EntityEnclosingRequestWrapper)request;
                    Header content_encoding = post.getFirstHeader("Content-Encoding");
                    if (content_encoding != null && content_encoding.getValue().equalsIgnoreCase("gzip")) {

                        ByteArrayOutputStream gzipped_bytes = new ByteArrayOutputStream();
                        GZIPOutputStream gzip = new GZIPOutputStream(gzipped_bytes);
                        InputStream in = post.getEntity().getContent();
                        byte[] tmp = new byte[2048];
                        int l;
                        while ((l = in.read(tmp)) != -1)
                            gzip.write(tmp, 0, l);
                        gzip.close();

                        post.setEntity(new ByteArrayEntity(gzipped_bytes.toByteArray()));
                    }
                }
            }
        }, 0);

        addResponseInterceptor(new HttpResponseInterceptor() {
            public void process(final HttpResponse response, final HttpContext context) throws HttpException, IOException {
                HttpEntity entity = response.getEntity();
                if (entity != null) {
                    Header ceheader = entity.getContentEncoding();
                    if (ceheader != null) {
                        HeaderElement[] codecs = ceheader.getElements();
                        for (int i = 0; i < codecs.length; i++) {
                            if (codecs[i].getName().equalsIgnoreCase("gzip")) {
                                response.setEntity(new GzipDecompressingEntity(response.getEntity()));
                                return;
                            }
                        }
                    }
                }
            }
        });
    }
}
