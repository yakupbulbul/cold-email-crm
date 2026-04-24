// Reverse proxy for Claude preview tool → forwards to the running cold-mail
// frontend at port 3010.
//
// Two critical fixes applied here:
//
// FIX 1 — WebSocket proxying (the hydration blocker):
//   Next.js 16 dev mode passes a `debugChannel` to React's
//   `createFromReadableStream`. React waits for BOTH the inline RSC stream
//   AND the debugChannel to close before resolving `initialServerResponse`.
//   The debugChannel is written to by the HMR WebSocket. Without WebSocket
//   support in the proxy the WebSocket never connects, the debug channel
//   never closes, and `hydrateRoot()` is never called.
//
// FIX 2 — Hoist `self.__next_r` into <head>:
//   Next.js places `<script id="_R_">self.__next_r="…"</script>` in <body>,
//   but createWebSocket() and createDebugChannel() throw InvariantErrors if
//   self.__next_r is falsy. On fast localhost connections main-app.js (async,
//   in <head>) can execute before those body scripts. We buffer HTML responses
//   and move the tag into <head> as a defence-in-depth measure.

const http = require('http');
const net  = require('net');
const zlib = require('zlib');

const TARGET_PORT = 3010;
const PROXY_PORT  = parseInt(process.env.PORT || '3020', 10);

// ─── hop-by-hop header filtering ────────────────────────────────────────────
const HOP_BY_HOP = new Set([
  'transfer-encoding', 'content-encoding', 'connection',
  'keep-alive', 'proxy-authenticate', 'proxy-authorization',
  'te', 'trailers', 'upgrade',
]);

function filterHeaders(headers) {
  const out = {};
  for (const [k, v] of Object.entries(headers)) {
    if (!HOP_BY_HOP.has(k.toLowerCase())) out[k] = v;
  }
  return out;
}

// ─── decompression helper ────────────────────────────────────────────────────
function decompress(buf, encoding) {
  return new Promise((resolve, reject) => {
    if (encoding === 'gzip')    return zlib.gunzip(buf, (e, r) => e ? reject(e) : resolve(r));
    if (encoding === 'br')      return zlib.brotliDecompress(buf, (e, r) => e ? reject(e) : resolve(r));
    if (encoding === 'deflate') return zlib.inflate(buf, (e, r) => e ? reject(e) : resolve(r));
    resolve(buf);
  });
}

// ─── HTML rewrite: hoist self.__next_r into <head> (FIX 2) ──────────────────
function hoistNextR(html) {
  const m = html.match(/<script id="_R_">self\.__next_r="([^"]+)"<\/script>/);
  if (!m) return html;
  html = html.replace(m[0], '');
  html = html.replace('<head>', `<head><script>self.__next_r="${m[1]}"</script>`);
  return html;
}

// ─── HTTP proxy ──────────────────────────────────────────────────────────────
const server = http.createServer((req, res) => {
  const options = {
    hostname : '127.0.0.1',
    port     : TARGET_PORT,
    path     : req.url,
    method   : req.method,
    headers  : { ...req.headers, host: `127.0.0.1:${TARGET_PORT}` },
  };

  const proxy = http.request(options, async (proxyRes) => {
    const encoding    = proxyRes.headers['content-encoding'] || '';
    const contentType = proxyRes.headers['content-type'] || '';
    const isHtml      = contentType.includes('text/html');
    const safeHeaders = filterHeaders(proxyRes.headers);

    try {
      if (isHtml) {
        const chunks = [];
        for await (const chunk of proxyRes) chunks.push(chunk);
        const raw = Buffer.concat(chunks);
        const decompressed = await decompress(raw, encoding);
        let html = decompressed.toString('utf8');
        html = hoistNextR(html);
        const outBuf = Buffer.from(html, 'utf8');
        safeHeaders['content-length'] = String(outBuf.length);
        delete safeHeaders['content-encoding'];
        res.writeHead(proxyRes.statusCode, safeHeaders);
        res.end(outBuf);
      } else if (encoding === 'gzip' || encoding === 'br' || encoding === 'deflate') {
        const decomp = encoding === 'gzip'    ? zlib.createGunzip()
                     : encoding === 'br'      ? zlib.createBrotliDecompress()
                     :                          zlib.createInflate();
        res.writeHead(proxyRes.statusCode, safeHeaders);
        proxyRes.pipe(decomp).pipe(res);
      } else {
        res.writeHead(proxyRes.statusCode, safeHeaders);
        proxyRes.pipe(res, { end: true });
      }
    } catch (err) {
      if (!res.headersSent) res.writeHead(502);
      res.end(`Proxy rewrite error: ${err.message}`);
    }
  });

  proxy.on('error', (err) => {
    if (!res.headersSent) res.writeHead(502);
    res.end(`Proxy error: ${err.message}`);
  });

  req.pipe(proxy, { end: true });
});

// ─── WebSocket proxy (FIX 1) ────────────────────────────────────────────────
// When the browser sends an HTTP Upgrade request (WebSocket handshake), we
// open a raw TCP connection to the target and tunnel the bytes in both
// directions. This lets the HMR WebSocket connect straight through to the
// Next.js dev server so the debug channel can close normally.
server.on('upgrade', (req, clientSocket, head) => {
  const targetSocket = net.connect(TARGET_PORT, '127.0.0.1', () => {
    // Forward the original Upgrade request to the target.
    const requestLine = `${req.method} ${req.url} HTTP/${req.httpVersion}\r\n`;
    const headers = Object.entries(req.headers)
      .map(([k, v]) => `${k}: ${v}`)
      .join('\r\n');
    targetSocket.write(`${requestLine}${headers}\r\n\r\n`);
    if (head && head.length > 0) targetSocket.write(head);

    // Bidirectional tunnel.
    targetSocket.pipe(clientSocket);
    clientSocket.pipe(targetSocket);
  });

  targetSocket.on('error', (err) => {
    console.error(`[cold-mail proxy] WebSocket tunnel error: ${err.message}`);
    clientSocket.destroy();
  });

  clientSocket.on('error', () => targetSocket.destroy());
});

server.listen(PROXY_PORT, '127.0.0.1', () => {
  console.log(`[cold-mail proxy] http://127.0.0.1:${PROXY_PORT}  →  http://127.0.0.1:${TARGET_PORT}`);
  console.log(`[cold-mail proxy] WebSocket tunnel enabled`);
  console.log(`[cold-mail proxy] HTML rewrite: self.__next_r hoisted into <head>`);
});
