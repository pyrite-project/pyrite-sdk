try:
    from .outline import DebugEnhancedPlugin
except ImportError:
    from outline import DebugEnhancedPlugin


plugin = DebugEnhancedPlugin()
plugin.start()
