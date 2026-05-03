'use client';

import Link from 'next/link';
import { Alert, Button } from 'react-bootstrap';

export default function LegacyPage() {
  return (
    <main className="container py-5" style={{ maxWidth: '760px' }}>
      <Alert variant="secondary">
        <Alert.Heading>Vista antigua</Alert.Heading>
        <p className="mb-0">
          Esta ruta se conservó solo como respaldo interno. La experiencia principal está en la página de inicio.
        </p>
      </Alert>
      <Link href="/" passHref legacyBehavior>
        <Button as="a" variant="outline-secondary">Volver al producto actual</Button>
      </Link>
    </main>
  );
}
