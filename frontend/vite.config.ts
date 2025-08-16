import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'

// SSL 인증서 파일 존재 여부 확인
const sslKeyPath = path.resolve(__dirname, './ssl/privkey.pem')
const sslCertPath = path.resolve(__dirname, './ssl/fullchain.pem')
const hasSSL = fs.existsSync(sslKeyPath) && fs.existsSync(sslCertPath)

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@/components': path.resolve(__dirname, './src/components'),
      '@/lib': path.resolve(__dirname, './src/lib'),
      '@/types': path.resolve(__dirname, './src/types'),
      '@/utils': path.resolve(__dirname, './src/utils'),
      '@/hooks': path.resolve(__dirname, './src/hooks'),
      '@/services': path.resolve(__dirname, './src/services')
    }
  },
  server: {
    port: 3000,
    host: true,
    ...(hasSSL && {
      https: {
        key: fs.readFileSync(sslKeyPath),
        cert: fs.readFileSync(sslCertPath)
      }
    }),
    allowedHosts: ['actlog.shop', 'localhost'],
    hmr: {
      host: 'actlog.shop',
      port: 3000,
      clientPort: 3000,
      ...(hasSSL && { protocol: 'wss' })
    },
    proxy: {
      '/api': {
        target: 'http://java-backend:8080', 
        changeOrigin: true
      },
      '/ai': {
        target: 'http://ai-api:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        entryFileNames: 'assets/[name].[hash].js',
        chunkFileNames: 'assets/[name].[hash].js',
        assetFileNames: 'assets/[name].[hash].[ext]'
      }
    }
  }
})