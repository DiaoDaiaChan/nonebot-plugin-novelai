from .load_balance import get_vram



class backend():

    def __init__(
        self, 
        backend_site
    ) -> None:
        self.backend_site = backend_site
        self.gpu_model = ""
        self.gpu_vram = []

    async def get_model_and_vram(self):
        self.gpu_vram = await get_vram(self.backend_site, True)
        
    


        