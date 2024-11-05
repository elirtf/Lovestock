document.addEventListener('DOMContentLoaded', function() {
    // Initialize mini charts
    function initializeMiniCharts() {
        document.querySelectorAll('.stock-card').forEach(card => {
            const canvas = card.querySelector('.stock-mini-chart');
            if (!canvas) return;

            try {
                const chartData = JSON.parse(card.dataset.chart || '[]');
                const isPositive = card.querySelector('.stock-change').classList.contains('positive');
                const ctx = canvas.getContext('2d');
                drawMiniChart(ctx, chartData, isPositive);
            } catch (error) {
                console.error('Error initializing chart:', error);
            }
        });
    }

    // Draw mini chart
    function drawMiniChart(ctx, data, isPositive) {
        if (!ctx || !data || !data.length) return;

        const width = ctx.canvas.width;
        const height = ctx.canvas.height;

        // Clear canvas
        ctx.clearRect(0, 0, width, height);

        // Calculate min/max for scaling
        const min = Math.min(...data);
        const max = Math.max(...data);
        const range = max - min || 1; // Prevent division by zero

        // Draw line with gradient
        ctx.beginPath();
        ctx.strokeStyle = isPositive ? '#00C805' : '#FF5000';
        ctx.lineWidth = 1.5;

        // Create gradient fill
        const gradient = ctx.createLinearGradient(0, 0, 0, height);
        if (isPositive) {
            gradient.addColorStop(0, 'rgba(0, 200, 5, 0.1)');
            gradient.addColorStop(1, 'rgba(0, 200, 5, 0)');
        } else {
            gradient.addColorStop(0, 'rgba(255, 80, 0, 0.1)');
            gradient.addColorStop(1, 'rgba(255, 80, 0, 0)');
        }

        // Draw path
        data.forEach((price, index) => {
            const x = (index / (data.length - 1)) * width;
            const y = height - ((price - min) / range) * (height * 0.8);

            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });

        // Stroke the line
        ctx.stroke();

        // Fill the area under the line
        ctx.lineTo(width, height);
        ctx.lineTo(0, height);
        ctx.fillStyle = gradient;
        ctx.fill();
    }


    // Start real-time updates
    function startRealTimeUpdates() {
        setInterval(() => {
            document.querySelectorAll('.stock-card').forEach(card => {
                const symbol = card.dataset.symbol;
                if (!symbol) return; // Skip if no symbol found

                fetch(`/api/stock/${symbol}/latest`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data && !data.error) {
                        updateStockCard(card, data);
                    }
                })
                .catch(error => {
                    console.error(`Error updating ${symbol}:`, error);
                    // Optionally stop updates for this card if there are persistent errors
                    // card.classList.add('update-error');
                });
        });
    }, 3000); // Update every 3 seconds
}

    function updateStockCard(card, data) {
        try {
            const priceEl = card.querySelector('.stock-price');
            const changeEl = card.querySelector('.stock-change');
            const volumeEl = card.querySelector('.stock-volume');
            const canvas = card.querySelector('.stock-mini-chart');

            if (!priceEl || !changeEl || !volumeEl || !canvas) {
                console.warn('Missing elements in stock card:', card);
                return;
            }

            // Update price with animation
            const oldPrice = parseFloat(priceEl.textContent.replace('$', ''));
            const newPrice = data.price;

            if (!isNaN(newPrice)) {
                priceEl.textContent = `$${newPrice.toFixed(2)}`;
                priceEl.classList.remove('flash-green', 'flash-red');
                void priceEl.offsetWidth; // Trigger reflow
                priceEl.classList.add(newPrice > oldPrice ? 'flash-green' : 'flash-red');
            }

            // Update change
            const isPositive = data.change >= 0;
            changeEl.className = `stock-change ${isPositive ? 'positive' : 'negative'}`;
            changeEl.innerHTML = `
                ${isPositive ? '↑' : '↓'} 
                $${Math.abs(data.change).toFixed(2)} 
                (${Math.abs(data.percent_change).toFixed(2)}%)
            `;

            // Update volume
            volumeEl.textContent = `Vol: ${data.volume}`;

            // Update chart if chart data exists
            if (data.chart_data && Array.isArray(data.chart_data)) {
                const ctx = canvas.getContext('2d');
                drawMiniChart(ctx, data.chart_data, isPositive);
            }

            // Remove flash animation
            setTimeout(() => {
                priceEl.classList.remove('flash-green', 'flash-red');
            }, 1000);

        } catch (error) {
            console.error('Error updating stock card:', error);
        }
    }



    // Initialize everything
    function initialize() {
        initializeMiniCharts();
        startRealTimeUpdates();

        // Make stock cards clickable
        document.querySelectorAll('.stock-card').forEach(card => {
            card.addEventListener('click', function(e) {
                if (!e.target.closest('.watchlist-form') && !e.target.closest('.remove-form')) {
                    const symbol = this.dataset.symbol;
                    window.location.href = `/stock/${symbol}`;
                }
            });
        });
    }

    // Start the application
    initialize();
});