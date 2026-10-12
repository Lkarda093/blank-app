import test from 'node:test';
import assert from 'node:assert/strict';
import { api } from './api.js';
test('sends owner bearer and JSON without putting token in URL', async () => {
  globalThis.fetch = async (url, options) => { assert.equal(url, '/api/config'); assert.equal(options.headers.Authorization, 'Bearer owner'); return new Response(JSON.stringify({configured:true})); };
  assert.deepEqual(await api('/config', 'owner'), {configured:true});
});
test('handles deletion without JSON', async () => { globalThis.fetch = async () => new Response(null, {status:204}); assert.equal(await api('/conversations/id', 'owner', {method:'DELETE'}), null); });
test('preserves actionable quota error', async () => { globalThis.fetch = async () => new Response(JSON.stringify({detail:'Cota esgotada'}), {status:429}); await assert.rejects(api('/x', 'owner'), /Cota esgotada/); });
test('handles disconnected server', async () => { globalThis.fetch = async () => { throw new TypeError('Failed to fetch'); }; await assert.rejects(api('/x', 'owner'), /Sem conexão/); });
test('handles invalid proxy response', async () => { globalThis.fetch = async () => new Response('<html>Error</html>'); await assert.rejects(api('/x', 'owner'), /Resposta inválida/); });
test('session requests use same-origin cookies and CSRF header without a bearer token', async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(options.credentials,'same-origin');
    assert.equal(options.headers['X-Aurora-Request'],'1');
    assert.equal(options.headers.Authorization,undefined);
    return new Response(JSON.stringify({authenticated:true}));
  };
  assert.deepEqual(await api('/auth/session'),{authenticated:true});
});
