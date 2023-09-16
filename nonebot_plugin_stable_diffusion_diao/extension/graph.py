import matplotlib.pyplot as plt

from io import BytesIO
from ..config import redis_client


class GraphDrawer:
    def __init__(
        self, x: list, y: list, 
        x_name: str, y_name: str, 
        title: str
    ):
        self.x = x
        self.y = y
        self.x_name = x_name
        self.y_name = y_name
        self.title = title
    
    async def draw_and_return_graph(self) -> bytes:
        plt.figure()
        
        plt.plot(self.x, self.y)
        plt.title(self.title)
        plt.xlabel(self.x_name)
        plt.ylabel(self.y_name)
        
        buffer = BytesIO()
        plt.savefig(buffer, format="png")
        buffer.seek(0)
        graph_byte = buffer.getvalue()
        
        plt.close()
        
        return graph_byte


