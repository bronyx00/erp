export function printBlob(blob: Blob) {
    const url = window.URL.createObjectURL(blob);

    // Crear un iframe invisible
    const iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    iframe.src = url;

    document.body.appendChild(iframe);

    iframe.onload = () => {
        if (iframe.contentWindow) {
            // Enfocar y mandar a imprimir
            iframe.contentWindow.focus();
            iframe.contentWindow.print();

            // Limpieza después de imprimir (o cancelar)
            // Timeout para asegurar que terminó la impresión
            setTimeout(() => {
                document.body.removeChild(iframe);
                window.URL.revokeObjectURL(url);
            }, 1000);
        }
    };
}