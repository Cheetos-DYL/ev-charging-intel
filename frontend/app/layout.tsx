import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'EV Charging Market Intelligence',
  description: 'A regional intelligence archive for the EV charging market.',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
