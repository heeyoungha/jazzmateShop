import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'

// SSL 인증서 파일 존재 여부 확인
const sslKeyPath = path.resolve(__dirname, './ssl/privkey.pem')
const sslCertPath = path.resolve(__dirname, './ssl/fullchain.pem')
const hasSSL = fs.existsSync(sslKeyPath) && fs.existsSync(sslCertPath)

// 운영 환경 여부 확인 (nginx가 있는 경우)
const isProduction = process.env.NODE_ENV === 'production' || hasSSL
const isDocker = process.env.VITE_DOCKER === 'true'

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
    // 프록시 설정
    // 운영 환경에서는 nginx가 프록시를 처리하므로 Vite 프록시 비활성화
    // Docker 환경에서는 Docker 서비스 이름 사용, 로컬 개발 환경에서는 localhost 사용
    ...(isProduction ? {} : {
      proxy: {
        '/api': {
          target: isDocker ? 'http://java-backend:8080' : (process.env.VITE_API_URL || 'http://localhost:8080'), 
          changeOrigin: true,
          // rewrite 제거: 백엔드는 이미 /api 경로를 포함하고 있음
        },
        '/ai-api': {
          target: isDocker ? 'http://ai-api:8000' : (process.env.VITE_AI_SERVICE_URL || 'http://localhost:8000'),
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/ai-api/, '')
        }
      }
    })
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