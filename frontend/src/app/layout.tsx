import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'KarmaSystem — Сервис лояльности',
  description: 'Привлекайте и удерживайте клиентов с помощью системы лояльности KarmaSystem',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru">
      <body className="min-h-screen bg-white text-black">
        <main>
          {children}
        </main>
      </body>
    </html>
  );
}
