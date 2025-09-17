import { NextResponse, NextRequest } from 'next/server'

// Public paths that do not require auth
const PUBLIC_PATHS = [
  '/login',
  '/_next',
  '/favicon.ico',
  '/robots.txt',
  '/sitemap.xml',
  '/api', // let API proxy pass
  '/auth', // allow auth endpoints
  '/health', // health check endpoint
]

function isPublic(pathname: string){
  return PUBLIC_PATHS.some(p => pathname === p || pathname.startsWith(p + '/'))
}

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl
  if (isPublic(pathname)) return NextResponse.next()

  // Get token from cookies
  const token = req.cookies.get('auth_token')?.value
  if (!token) {
    const url = req.nextUrl.clone()
    url.pathname = '/login'
    url.searchParams.set('next', pathname)
    return NextResponse.redirect(url)
  }
  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!.*\\.\w+$).*)'] // match all paths except static files
}
