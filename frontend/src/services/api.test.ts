import test from 'node:test';
import assert from 'node:assert';
import { resolveApiBase } from './api.ts';

test('1. VITE_API_URL absolute URL', () => {
  const result = resolveApiBase('https://nagarsetu-s8qy.onrender.com/api/v1', undefined);
  assert.strictEqual(result, 'https://nagarsetu-s8qy.onrender.com/api/v1');
});

test('2. VITE_API_BASE_URL absolute URL', () => {
  const result = resolveApiBase(undefined, 'https://nagarsetu-s8qy.onrender.com/api/v1');
  assert.strictEqual(result, 'https://nagarsetu-s8qy.onrender.com/api/v1');
});

test('3. URL without /api/v1', () => {
  const result = resolveApiBase('https://nagarsetu-s8qy.onrender.com');
  assert.strictEqual(result, 'https://nagarsetu-s8qy.onrender.com/api/v1');
});

test('4. URL with /api/v1', () => {
  const result = resolveApiBase('https://nagarsetu-s8qy.onrender.com/api/v1');
  assert.strictEqual(result, 'https://nagarsetu-s8qy.onrender.com/api/v1');
});

test('5. URL with trailing slash', () => {
  const result1 = resolveApiBase('https://nagarsetu-s8qy.onrender.com/');
  assert.strictEqual(result1, 'https://nagarsetu-s8qy.onrender.com/api/v1');
  const result2 = resolveApiBase('https://nagarsetu-s8qy.onrender.com/api/v1/');
  assert.strictEqual(result2, 'https://nagarsetu-s8qy.onrender.com/api/v1');
});

test('6. No duplicate /api/v1', () => {
  const result = resolveApiBase('https://nagarsetu-s8qy.onrender.com/api/v1');
  assert.strictEqual(result, 'https://nagarsetu-s8qy.onrender.com/api/v1');
  assert.strictEqual(result.includes('/api/v1/api/v1'), false);
});

test('7. Localhost fallback (when neither env var is provided)', () => {
  const nodeFallback = resolveApiBase(undefined, undefined, false);
  assert.strictEqual(nodeFallback, 'http://localhost:8000/api/v1');
  const browserFallback = resolveApiBase(undefined, undefined, true);
  assert.strictEqual(browserFallback, '/api/v1');
});
