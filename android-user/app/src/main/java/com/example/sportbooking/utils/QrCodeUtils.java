package com.example.sportbooking.utils;

import android.graphics.Bitmap;

import com.google.zxing.BarcodeFormat;
import com.google.zxing.EncodeHintType;
import com.google.zxing.MultiFormatWriter;
import com.google.zxing.common.BitMatrix;

import java.util.EnumMap;
import java.util.Map;

public final class QrCodeUtils {

    private QrCodeUtils() {
    }

    public static Bitmap generateQRCode(
            String content,
            int width,
            int height
    ) throws Exception {

        if (content == null || content.trim().isEmpty()) {
            throw new IllegalArgumentException(
                    "QR Code content cannot be empty."
            );
        }

        Map<EncodeHintType, Object> hints =
                new EnumMap<>(EncodeHintType.class);

        hints.put(EncodeHintType.MARGIN, 1);

        BitMatrix matrix = new MultiFormatWriter().encode(
                content,
                BarcodeFormat.QR_CODE,
                width,
                height,
                hints
        );

        Bitmap bitmap = Bitmap.createBitmap(
                width,
                height,
                Bitmap.Config.RGB_565
        );

        for (int x = 0; x < width; x++) {
            for (int y = 0; y < height; y++) {
                bitmap.setPixel(
                        x,
                        y,
                        matrix.get(x, y)
                                ? 0xFF000000
                                : 0xFFFFFFFF
                );
            }
        }

        return bitmap;
    }
}