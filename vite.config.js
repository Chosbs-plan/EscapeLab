import { defineConfig } from 'vite';

// base './' : 빌드 결과를 어떤 하위 경로(예: GitHub Pages /EscapeLab/)에 올려도 동작하게 상대 경로로 만든다.
export default defineConfig({
  base: './',
});
