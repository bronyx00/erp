from abc import ABC, abstractmethod

class FiscalAdapter(ABC):
    """
    Clase base abstracta. Define qué debe saber hacer CUALQUIER adaptador de país.
    """
    @abstractmethod
    def process_invoice(self, invoice_data: dict) -> dict:
        """Recibe datos de factura y devuelve datos fiscales."""
        pass
    