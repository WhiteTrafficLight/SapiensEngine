import React from 'react';
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
// import Header from '@/components/ui/Header';
// import Footer from '@/components/ui/Footer';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'AgoraMind - Philosophical Dialogue Platform',
  description: 'A platform for collaborative knowledge creation through philosophical dialogues between humans and AI.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} flex flex-col min-h-screen`}>
        {/* <Header /> */}
        <main className="flex-grow">{children}</main>
        {/* <Footer /> */}
      </body>
    </html>
  );
}
