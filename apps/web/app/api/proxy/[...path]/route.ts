import { NextRequest } from "next/server";

const BACKEND = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

async function forward(req: NextRequest, params: { path: string[] }, method: string) {
  const target = `${BACKEND}/${params.path.join("/")}${req.nextUrl.search}`;
  const init: RequestInit = {
    method,
    headers: filterHeaders(req.headers),
    body: ["GET", "HEAD"].includes(method) ? undefined : await req.arrayBuffer(),
    // @ts-expect-error: undici-only field, Next 14 runtime supports it
    duplex: "half",
  };
  const upstream = await fetch(target, init);
  return new Response(upstream.body, {
    status: upstream.status,
    headers: passthroughHeaders(upstream.headers),
  });
}

function filterHeaders(h: Headers): HeadersInit {
  const out = new Headers();
  h.forEach((v, k) => {
    if (!["host", "connection", "content-length"].includes(k.toLowerCase())) out.set(k, v);
  });
  return out;
}

function passthroughHeaders(h: Headers): HeadersInit {
  const out = new Headers();
  h.forEach((v, k) => out.set(k, v));
  return out;
}

export async function GET(req: NextRequest, ctx: { params: { path: string[] } }) {
  return forward(req, ctx.params, "GET");
}
export async function POST(req: NextRequest, ctx: { params: { path: string[] } }) {
  return forward(req, ctx.params, "POST");
}
export async function PUT(req: NextRequest, ctx: { params: { path: string[] } }) {
  return forward(req, ctx.params, "PUT");
}
export async function DELETE(req: NextRequest, ctx: { params: { path: string[] } }) {
  return forward(req, ctx.params, "DELETE");
}

export const dynamic = "force-dynamic";
