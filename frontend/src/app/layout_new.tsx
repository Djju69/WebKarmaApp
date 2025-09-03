export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru">
      <body>
        <main>
          {children}
        </main>
      </body>
    </html>
  );
}

export const metadata = {
  title: 'KarmaSystem — Сервис лояльности',
  description: 'Привлекайте и удерживайте клиентов с помощью системы лояльности KarmaSystem',
};
