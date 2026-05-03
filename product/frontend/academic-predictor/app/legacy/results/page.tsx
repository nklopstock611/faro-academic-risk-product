'use client';

import Link from 'next/link';
import { Alert, Button } from 'react-bootstrap';

export default function LegacyResultsPage() {
  return (
    <main className="container py-5" style={{ maxWidth: '760px' }}>
      <Alert variant="secondary">
        <Alert.Heading>Resultados antiguos</Alert.Heading>
        <p className="mb-0">
          Esta ruta quedó solo como referencia interna. El flujo vigente usa la pantalla principal y sus resultados actuales.
        </p>
      </Alert>
      <Link href="/" passHref legacyBehavior>
        <Button as="a" variant="outline-secondary">Ir al producto actual</Button>
      </Link>
    </main>
  );
}
