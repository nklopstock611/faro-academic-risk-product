async function predecirExito(estudianteId, cursos) {
    const response = await fetch('http://localhost:8000/predecir', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            estudiante_id: estudianteId,
            cursos: cursos
        })
    });

    const resultado = await response.json();

    // Mostrar resultado
    console.log(`Probabilidad: ${resultado.probabilidad_exito * 100}%`);
    console.log(`Confianza: ${resultado.confianza}`);

    return resultado;
}

// Uso
predecirExito('EST_00000045', ['CRS_00017889', 'CRS_00017890', 'CRS_00017891'])
    .then(res => {
        document.getElementById('probabilidad').textContent =
            `${(res.probabilidad_exito * 100).toFixed(1)}%`;
        document.getElementById('confianza').textContent = res.confianza;
    });