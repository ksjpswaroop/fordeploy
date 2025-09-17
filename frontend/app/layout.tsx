import './globals.css';
import React from 'react';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Temp Next App',
  description: 'Scaffold test app'
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <main style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
          {children}
        </main>
      </body>
    </html>
  );
}
