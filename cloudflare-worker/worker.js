/**
 * Cloudflare Worker - Instagram Scraper Relay para Instaloader API
 *
 * Como usar na Cloudflare (100% Gratuito - até 100.000 req/dia):
 * 1. Acesse o painel da Cloudflare -> Workers & Pages -> Create -> Create Worker
 * 2. Dê um nome (ex: ig-relay) e clique em Deploy
 * 3. Clique em "Edit Code", cole todo este código e clique em "Deploy"
 * 4. Copie a URL gerada (ex: https://ig-relay.seu-nome.workers.dev)
 * 5. No Dokploy (aba Environment), adicione:
 *      CF_WORKER_URL=https://ig-relay.seu-nome.workers.dev
 */

export default {
  async fetch(request, env) {
    // CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "*",
        },
      });
    }

    // Validação opcional de token secreto (se configurado no Worker e no Dokploy via CF_WORKER_SECRET)
    if (env && env.RELAY_SECRET) {
      const provided = request.headers.get("X-Relay-Secret");
      if (provided !== env.RELAY_SECRET) {
        return new Response(JSON.stringify({ error: "Unauthorized relay secret" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        });
      }
    }

    const reqUrl = new URL(request.url);
    let targetUrl = reqUrl.searchParams.get("url");
    let customUa = reqUrl.searchParams.get("ua") || "curl/8.5.0";
    let method = "GET";
    let customHeaders = {};
    let body = undefined;

    if (request.method === "POST") {
      try {
        const payload = await request.json();
        targetUrl = payload.url || targetUrl;
        customUa = payload.ua || customUa;
        method = payload.method || "GET";
        customHeaders = payload.headers || {};
        body = payload.body || undefined;
      } catch {
        return new Response(JSON.stringify({ error: "Invalid JSON payload" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
    }

    if (!targetUrl || !targetUrl.includes("instagram.com")) {
      return new Response(
        JSON.stringify({
          status: "ok",
          service: "Instaloader Cloudflare Worker Relay",
          usage: "?url=https://www.instagram.com/p/SHORTCODE/embed/captioned/",
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    const fetchHeaders = new Headers({
      "User-Agent": customUa,
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language": "en-US,en;q=0.9",
      ...customHeaders,
    });

    try {
      const response = await fetch(targetUrl, {
        method,
        headers: fetchHeaders,
        body: method === "POST" ? body : undefined,
        redirect: "follow",
      });

      const text = await response.text();
      return new Response(text, {
        status: response.status,
        headers: {
          "Content-Type": response.headers.get("Content-Type") || "text/html; charset=utf-8",
          "X-Final-Url": response.url || targetUrl,
          "Access-Control-Allow-Origin": "*",
        },
      });
    } catch (err) {
      return new Response(JSON.stringify({ error: String(err) }), {
        status: 502,
        headers: { "Content-Type": "application/json" },
      });
    }
  },
};
