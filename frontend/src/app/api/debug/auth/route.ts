import { NextRequest } from 'next/server';

export async function GET(request: NextRequest) {
  const cookies = request.headers.get('cookie') || '';
  const headers = Object.fromEntries(request.headers.entries());
  
  return Response.json({
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV,
    auth0Config: {
      domain: process.env.AUTH0_ISSUER_BASE_URL ? 'Set' : 'Missing',
      clientId: process.env.AUTH0_CLIENT_ID ? 'Set' : 'Missing',
      clientSecret: process.env.AUTH0_CLIENT_SECRET ? 'Set' : 'Missing',
      baseUrl: process.env.AUTH0_BASE_URL ? 'Set' : 'Missing',
      secret: process.env.AUTH0_SECRET ? 'Set' : 'Missing',
    },
    cookies: {
      raw: cookies,
      parsed: cookies ? cookies.split('; ').reduce((acc, cookie) => {
        const [key, value] = cookie.split('=');
        acc[key] = value;
        return acc;
      }, {} as Record<string, string>) : {},
      hasAuthCookie: cookies.includes('auth-user=')
    },
    headers: headers,
    url: request.url
  }, { status: 200 });
}
