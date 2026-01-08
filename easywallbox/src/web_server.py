"""Web Server for EasyWallbox Dashboard."""
import logging
import os
import aiohttp.web
import jinja2
import aiohttp_jinja2

log = logging.getLogger(__name__)

class WebServer:
    def __init__(self, coordinator):
        self._coordinator = coordinator
        self._app = aiohttp.web.Application()
        self._runner = None
        self._site = None
        
        # Setup Jinja2 templates
        template_path = os.path.join(os.path.dirname(__file__), 'templates')
        aiohttp_jinja2.setup(self._app, loader=jinja2.FileSystemLoader(template_path))
        
        # Setup routes
        self._app.router.add_get('/', self.handle_index)
        self._app.router.add_get('/api/status', self.handle_status)
        self._app.router.add_post('/api/reconnect/ble', self.handle_reconnect_ble)
        self._app.router.add_post('/api/limit/{type}', self.handle_set_limit)
        self._app.router.add_post('/api/refresh', self.handle_refresh)

    async def start(self):
        """Start the web server."""
        log.info("Starting Web Server on port 8099...")
        self._runner = aiohttp.web.AppRunner(self._app)
        await self._runner.setup()
        self._site = aiohttp.web.TCPSite(self._runner, '0.0.0.0', 8099)
        await self._site.start()

    async def stop(self):
        """Stop the web server."""
        if self._runner:
            await self._runner.cleanup()

    @aiohttp_jinja2.template('index.html')
    async def handle_index(self, request):
        """Serve the dashboard."""
        return {}

    async def handle_status(self, request):
        """Return current status."""
        status = self._coordinator.get_status()
        return aiohttp.web.json_response(status)

    async def handle_reconnect_ble(self, request):
        """Trigger BLE reconnection."""
        await self._coordinator.reconnect_ble()
        return aiohttp.web.json_response({'status': 'ok'})

    async def handle_set_limit(self, request):
        """Set a limit."""
        limit_type = request.match_info['type']
        try:
            data = await request.json()
            value = data.get('value')
            if value:
                await self._coordinator.set_limit(limit_type, value)
                return aiohttp.web.json_response({'status': 'ok'})
        except Exception as e:
            log.error(f"Error setting limit: {e}")
        return aiohttp.web.Response(status=400)

    async def handle_refresh(self, request):
        """Trigger data refresh."""
        await self._coordinator.refresh_data()
        return aiohttp.web.json_response({'status': 'ok'})
