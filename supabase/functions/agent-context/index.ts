const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Content-Type": "application/json",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  const url = new URL(req.url);
  const probe = url.searchParams.get("probe");

  if (probe === "1") {
    return new Response(
      JSON.stringify({
        status: "ok",
        message: "Personal Agent context endpoint is live",
        context_layer: "ready",
      }),
      {
        status: 200,
        headers: corsHeaders,
      }
    );
  }

  return new Response(
    JSON.stringify({
      status: "auth_required",
      message: "Authenticated agent context will be added next",
    }),
    {
      status: 200,
      headers: corsHeaders,
    }
  );
});