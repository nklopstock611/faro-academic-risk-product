import 'bootstrap/dist/css/bootstrap.min.css';
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Predictor Académico",
  description: "Herramienta para coordinadores académicos",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body>
        <div className="container py-4">
          {children}
        </div>
      </body>
    </html>
  );
}