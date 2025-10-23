"""
Performance monitoring and adaptive optimization for the collaboration server.
Monitors system resources and network conditions to optimize performance.
"""

import threading
import time
import logging
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    # Mock psutil for testing environments
    class MockPsutil:
        @staticmethod
        def cpu_percent(interval=None):
            return 50.0
        
        @staticmethod
        def virtual_memory():
            class MockMemory:
                percent = 60.0
            return MockMemory()
        
        @staticmethod
        def net_io_counters():
            class MockNetIO:
                bytes_sent = 1000
                bytes_recv = 1000
            return MockNetIO()
        
        @staticmethod
        def disk_io_counters():
            class MockDiskIO:
                read_bytes = 500
                write_bytes = 500
            return MockDiskIO()
    
    psutil = MockPsutil()
import statistics
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class NetworkMetrics:
    """Network performance metrics."""
    latency_ms: float
    packet_loss_rate: float
    bandwidth_utilization: float
    jitter_ms: float
    timestamp: float


@dataclass
class SystemMetrics:
    """System resource metrics."""
    cpu_usage_percent: float
    memory_usage_percent: float
    network_io_bytes_sent: int
    network_io_bytes_recv: int
    disk_io_read_bytes: int
    disk_io_write_bytes: int
    timestamp: float


class AdaptiveCompressionManager:
    """
    Manages adaptive compression based on network conditions and system resources.
    """
    
    def __init__(self):
        self.video_quality_levels = {
            'high': {'bitrate': 2000000, 'fps': 30, 'resolution_scale': 1.0},
            'medium': {'bitrate': 1000000, 'fps': 24, 'resolution_scale': 0.8},
            'low': {'bitrate': 500000, 'fps': 15, 'resolution_scale': 0.6},
            'minimal': {'bitrate': 250000, 'fps': 10, 'resolution_scale': 0.4}
        }
        
        self.audio_quality_levels = {
            'high': {'sample_rate': 44100, 'bitrate': 128000, 'channels': 2},
            'medium': {'sample_rate': 22050, 'bitrate': 64000, 'channels': 1},
            'low': {'sample_rate': 16000, 'bitrate': 32000, 'channels': 1},
            'minimal': {'sample_rate': 8000, 'bitrate': 16000, 'channels': 1}
        }
        
        self.current_video_quality = 'high'
        self.current_audio_quality = 'high'
        self._lock = threading.Lock()
    
    def adapt_quality_based_on_metrics(self, network_metrics: NetworkMetrics, 
                                     system_metrics: SystemMetrics) -> Dict[str, str]:
        """
        Adapt compression quality based on current metrics.
        
        Args:
            network_metrics: Current network performance metrics
            system_metrics: Current system resource metrics
            
        Returns:
            dict: Updated quality settings
        """
        with self._lock:
            # Determine optimal quality based on conditions
            new_video_quality = self._determine_video_quality(network_metrics, system_metrics)
            new_audio_quality = self._determine_audio_quality(network_metrics, system_metrics)
            
            # Update quality if changed
            quality_changed = False
            if new_video_quality != self.current_video_quality:
                logger.info(f"Adapting video quality: {self.current_video_quality} -> {new_video_quality}")
                self.current_video_quality = new_video_quality
                quality_changed = True
            
            if new_audio_quality != self.current_audio_quality:
                logger.info(f"Adapting audio quality: {self.current_audio_quality} -> {new_audio_quality}")
                self.current_audio_quality = new_audio_quality
                quality_changed = True
            
            return {
                'video_quality': self.current_video_quality,
                'audio_quality': self.current_audio_quality,
                'quality_changed': quality_changed
            }
    
    def _determine_video_quality(self, network_metrics: NetworkMetrics, 
                               system_metrics: SystemMetrics) -> str:
        """Determine optimal video quality based on metrics."""
        # High CPU usage -> reduce quality
        if system_metrics.cpu_usage_percent > 80:
            return 'low'
        
        # High packet loss -> reduce quality
        if network_metrics.packet_loss_rate > 0.05:  # 5% packet loss
            return 'minimal'
        elif network_metrics.packet_loss_rate > 0.02:  # 2% packet loss
            return 'low'
        
        # High latency -> reduce quality
        if network_metrics.latency_ms > 200:
            return 'low'
        elif network_metrics.latency_ms > 100:
            return 'medium'
        
        # High jitter -> reduce quality
        if network_metrics.jitter_ms > 50:
            return 'medium'
        
        # Good conditions -> high quality
        if (system_metrics.cpu_usage_percent < 50 and 
            network_metrics.latency_ms < 50 and 
            network_metrics.packet_loss_rate < 0.01):
            return 'high'
        
        return 'medium'  # Default to medium quality
    
    def _determine_audio_quality(self, network_metrics: NetworkMetrics, 
                               system_metrics: SystemMetrics) -> str:
        """Determine optimal audio quality based on metrics."""
        # Audio is more critical than video, so be more conservative
        
        # Very high CPU usage -> minimal quality
        if system_metrics.cpu_usage_percent > 90:
            return 'minimal'
        
        # High packet loss -> reduce quality
        if network_metrics.packet_loss_rate > 0.03:  # 3% packet loss
            return 'low'
        
        # High latency -> reduce quality
        if network_metrics.latency_ms > 150:
            return 'low'
        elif network_metrics.latency_ms > 75:
            return 'medium'
        
        # Good conditions -> high quality
        if (system_metrics.cpu_usage_percent < 60 and 
            network_metrics.latency_ms < 30 and 
            network_metrics.packet_loss_rate < 0.005):
            return 'high'
        
        return 'medium'  # Default to medium quality
    
    def get_current_video_settings(self) -> Dict:
        """Get current video compression settings."""
        with self._lock:
            return self.video_quality_levels[self.current_video_quality].copy()
    
    def get_current_audio_settings(self) -> Dict:
        """Get current audio compression settings."""
        with self._lock:
            return self.audio_quality_levels[self.current_audio_quality].copy()


class PerformanceMonitor:
    """
    Monitors system performance and network conditions for adaptive optimization.
    """
    
    def __init__(self, monitoring_interval: float = 5.0):
        self.monitoring_interval = monitoring_interval
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # Metrics history (keep last 60 samples = 5 minutes at 5s intervals)
        self.network_metrics_history: deque = deque(maxlen=60)
        self.system_metrics_history: deque = deque(maxlen=60)
        
        # Adaptive compression manager
        self.compression_manager = AdaptiveCompressionManager()
        
        # Performance callbacks
        self.performance_callbacks: List[callable] = []
        
        # Network monitoring state
        self.last_network_io = None
        self.packet_loss_tracker = {}  # client_id -> packet tracking
        
        self._lock = threading.RLock()
    
    def start_monitoring(self) -> bool:
        """
        Start performance monitoring.
        
        Returns:
            bool: True if monitoring started successfully
        """
        if self.is_monitoring:
            logger.warning("Performance monitoring already running")
            return True
        
        try:
            self.is_monitoring = True
            
            # Initialize baseline metrics
            self.last_network_io = psutil.net_io_counters()
            
            # Start monitoring thread
            self.monitor_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True
            )
            self.monitor_thread.start()
            
            logger.info(f"Performance monitoring started (interval: {self.monitoring_interval}s)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start performance monitoring: {e}")
            self.is_monitoring = False
            return False
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        
        # Wait for monitoring thread to finish
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        
        logger.info("Performance monitoring stopped")
    
    def add_performance_callback(self, callback: callable):
        """
        Add callback to be notified of performance updates.
        
        Args:
            callback: Function to call with performance metrics
        """
        self.performance_callbacks.append(callback)
    
    def track_packet_loss(self, client_id: str, expected_sequence: int, received_sequence: int):
        """
        Track packet loss for a specific client.
        
        Args:
            client_id: ID of the client
            expected_sequence: Expected sequence number
            received_sequence: Actually received sequence number
        """
        with self._lock:
            if client_id not in self.packet_loss_tracker:
                self.packet_loss_tracker[client_id] = {
                    'expected_packets': 0,
                    'received_packets': 0,
                    'last_sequence': -1
                }
            
            tracker = self.packet_loss_tracker[client_id]
            
            # Calculate missed packets
            if tracker['last_sequence'] >= 0:
                expected_count = received_sequence - tracker['last_sequence']
                tracker['expected_packets'] += expected_count
                tracker['received_packets'] += 1  # This packet was received
            
            tracker['last_sequence'] = received_sequence
    
    def get_packet_loss_rate(self, client_id: str = None) -> float:
        """
        Get packet loss rate for a client or overall.
        
        Args:
            client_id: Specific client ID or None for overall rate
            
        Returns:
            float: Packet loss rate (0.0 to 1.0)
        """
        with self._lock:
            if client_id:
                if client_id not in self.packet_loss_tracker:
                    return 0.0
                
                tracker = self.packet_loss_tracker[client_id]
                if tracker['expected_packets'] == 0:
                    return 0.0
                
                return 1.0 - (tracker['received_packets'] / tracker['expected_packets'])
            
            # Calculate overall packet loss rate
            total_expected = sum(t['expected_packets'] for t in self.packet_loss_tracker.values())
            total_received = sum(t['received_packets'] for t in self.packet_loss_tracker.values())
            
            if total_expected == 0:
                return 0.0
            
            return 1.0 - (total_received / total_expected)
    
    def _monitoring_loop(self):
        """Main monitoring loop running in separate thread."""
        logger.info("Performance monitoring loop started")
        
        while self.is_monitoring:
            try:
                # Collect system metrics
                system_metrics = self._collect_system_metrics()
                
                # Collect network metrics
                network_metrics = self._collect_network_metrics()
                
                # Store metrics in history
                with self._lock:
                    self.system_metrics_history.append(system_metrics)
                    self.network_metrics_history.append(network_metrics)
                
                # Adapt compression based on metrics
                quality_update = self.compression_manager.adapt_quality_based_on_metrics(
                    network_metrics, system_metrics
                )
                
                # Notify callbacks if quality changed
                if quality_update['quality_changed']:
                    for callback in self.performance_callbacks:
                        try:
                            callback(quality_update, network_metrics, system_metrics)
                        except Exception as e:
                            logger.error(f"Error in performance callback: {e}")
                
                # Sleep until next monitoring cycle
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                if self.is_monitoring:
                    logger.error(f"Error in monitoring loop: {e}")
                break
        
        logger.info("Performance monitoring loop ended")
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect current system resource metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Network I/O
            net_io = psutil.net_io_counters()
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            
            return SystemMetrics(
                cpu_usage_percent=cpu_percent,
                memory_usage_percent=memory_percent,
                network_io_bytes_sent=net_io.bytes_sent,
                network_io_bytes_recv=net_io.bytes_recv,
                disk_io_read_bytes=disk_io.read_bytes if disk_io else 0,
                disk_io_write_bytes=disk_io.write_bytes if disk_io else 0,
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            # Return default metrics on error
            return SystemMetrics(
                cpu_usage_percent=0.0,
                memory_usage_percent=0.0,
                network_io_bytes_sent=0,
                network_io_bytes_recv=0,
                disk_io_read_bytes=0,
                disk_io_write_bytes=0,
                timestamp=time.time()
            )
    
    def _collect_network_metrics(self) -> NetworkMetrics:
        """Collect current network performance metrics."""
        try:
            # Calculate bandwidth utilization
            current_net_io = psutil.net_io_counters()
            bandwidth_utilization = 0.0
            
            if self.last_network_io:
                bytes_sent_diff = current_net_io.bytes_sent - self.last_network_io.bytes_sent
                bytes_recv_diff = current_net_io.bytes_recv - self.last_network_io.bytes_recv
                total_bytes = bytes_sent_diff + bytes_recv_diff
                
                # Estimate bandwidth utilization (assuming 100 Mbps connection)
                estimated_bandwidth_bps = 100 * 1024 * 1024 / 8  # 100 Mbps in bytes/sec
                bandwidth_utilization = min(1.0, total_bytes / (self.monitoring_interval * estimated_bandwidth_bps))
            
            self.last_network_io = current_net_io
            
            # Get packet loss rate
            packet_loss_rate = self.get_packet_loss_rate()
            
            # Estimate latency and jitter (simplified - in real implementation, 
            # you'd measure actual round-trip times)
            latency_ms = self._estimate_latency()
            jitter_ms = self._estimate_jitter()
            
            return NetworkMetrics(
                latency_ms=latency_ms,
                packet_loss_rate=packet_loss_rate,
                bandwidth_utilization=bandwidth_utilization,
                jitter_ms=jitter_ms,
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"Error collecting network metrics: {e}")
            # Return default metrics on error
            return NetworkMetrics(
                latency_ms=50.0,
                packet_loss_rate=0.0,
                bandwidth_utilization=0.0,
                jitter_ms=5.0,
                timestamp=time.time()
            )
    
    def _estimate_latency(self) -> float:
        """Estimate network latency based on system load and history."""
        # Simplified latency estimation
        # In a real implementation, you'd measure actual round-trip times
        
        # Base latency
        base_latency = 20.0  # 20ms base
        
        # Add latency based on CPU usage
        if self.system_metrics_history:
            recent_cpu = self.system_metrics_history[-1].cpu_usage_percent
            cpu_latency_factor = max(0, (recent_cpu - 50) / 50)  # Increase after 50% CPU
            base_latency += cpu_latency_factor * 30  # Up to 30ms additional
        
        # Add latency based on bandwidth utilization
        if self.network_metrics_history:
            recent_bandwidth = self.network_metrics_history[-1].bandwidth_utilization
            bandwidth_latency_factor = recent_bandwidth
            base_latency += bandwidth_latency_factor * 20  # Up to 20ms additional
        
        return min(base_latency, 200.0)  # Cap at 200ms
    
    def _estimate_jitter(self) -> float:
        """Estimate network jitter based on system variability."""
        # Simplified jitter estimation
        
        if len(self.system_metrics_history) < 3:
            return 5.0  # Default jitter
        
        # Calculate CPU usage variability as a proxy for jitter
        recent_cpu_values = [m.cpu_usage_percent for m in list(self.system_metrics_history)[-5:]]
        
        if len(recent_cpu_values) > 1:
            cpu_std_dev = statistics.stdev(recent_cpu_values)
            jitter = min(cpu_std_dev / 2, 25.0)  # Scale and cap jitter
            return max(jitter, 1.0)  # Minimum 1ms jitter
        
        return 5.0  # Default jitter
    
    def get_current_metrics(self) -> Tuple[Optional[NetworkMetrics], Optional[SystemMetrics]]:
        """
        Get the most recent metrics.
        
        Returns:
            tuple: (NetworkMetrics, SystemMetrics) or (None, None) if no data
        """
        with self._lock:
            network_metrics = self.network_metrics_history[-1] if self.network_metrics_history else None
            system_metrics = self.system_metrics_history[-1] if self.system_metrics_history else None
            return network_metrics, system_metrics
    
    def get_performance_summary(self) -> Dict:
        """
        Get performance summary and statistics.
        
        Returns:
            dict: Performance summary with averages and current values
        """
        with self._lock:
            summary = {
                'monitoring_active': self.is_monitoring,
                'samples_collected': len(self.system_metrics_history),
                'current_video_quality': self.compression_manager.current_video_quality,
                'current_audio_quality': self.compression_manager.current_audio_quality
            }
            
            if self.system_metrics_history:
                recent_system = list(self.system_metrics_history)[-10:]  # Last 10 samples
                summary.update({
                    'avg_cpu_usage': sum(m.cpu_usage_percent for m in recent_system) / len(recent_system),
                    'avg_memory_usage': sum(m.memory_usage_percent for m in recent_system) / len(recent_system),
                    'current_cpu_usage': recent_system[-1].cpu_usage_percent,
                    'current_memory_usage': recent_system[-1].memory_usage_percent
                })
            
            if self.network_metrics_history:
                recent_network = list(self.network_metrics_history)[-10:]  # Last 10 samples
                summary.update({
                    'avg_latency_ms': sum(m.latency_ms for m in recent_network) / len(recent_network),
                    'avg_packet_loss_rate': sum(m.packet_loss_rate for m in recent_network) / len(recent_network),
                    'avg_bandwidth_utilization': sum(m.bandwidth_utilization for m in recent_network) / len(recent_network),
                    'current_latency_ms': recent_network[-1].latency_ms,
                    'current_packet_loss_rate': recent_network[-1].packet_loss_rate,
                    'current_bandwidth_utilization': recent_network[-1].bandwidth_utilization
                })
            
            return summary
    
    def get_compression_manager(self) -> AdaptiveCompressionManager:
        """Get the adaptive compression manager."""
        return self.compression_manager