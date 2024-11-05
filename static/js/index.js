document.addEventListener('DOMContentLoaded', function() {
    // Initialize mini charts for all stock cards
    function initializeMiniCharts() {
        document.querySelectorAll('.stock-card').forEach(card => {
            const canvas = card.querySelector('.stock-mini-chart');
            if (!canvas) return;

            const ctx = canvas.getContext('2d');
            const chartData = JSON.parse(canvas.getAttribute('data-chart') || '[]');
            const isPositive = parseFloat(card.querySelector('.stock-change').textContent) >= 0;

            drawMiniChart(ctx, chartData, isPositive);
        });
    }

    // Draw mini chart on canvas
    function drawMiniChart(ctx, data, isPositive) {
        const width = ctx.canvas.width;
        const height = ctx.canvas.height;

        // Clear canvas
        ctx.clearRect(0, 0, width, height);

        if (!data || data.length < 2) return;

        // Calculate min/max for scaling
        const min = Math.min(...data);
        const max = Math.max(...data);
        const range = max - min || 1; // Prevent division by zero

        // Draw line
        ctx.beginPath();
        ctx.strokeStyle = isPositive ? '#00C805' : '#FF5000';
        ctx.lineWidth = 1.5;

        data.forEach((price, index) => {
            const x = (index / (data.length - 1)) * width;
            const y = height - ((price - min) / range) * (height * 0.8);

            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });

        ctx.stroke();

        // Add gradient fill
        const gradient = ctx.createLinearGradient(0, 0, 0, height);
        if (isPositive) {
            gradient.addColorStop(0, 'rgba(0, 200, 5, 0.1)');
            gradient.addColorStop(1, 'rgba(0, 200, 5, 0)');
        } else {
            gradient.addColorStop(0, 'rgba(255, 80, 0, 0.1)');
            gradient.addColorStop(1, 'rgba(255, 80, 0, 0)');
        }

        ctx.lineTo(width, height);
        ctx.lineTo(0, height);
        ctx.fillStyle = gradient;
        ctx.fill();
    }

    // Initialize charts
    initializeMiniCharts();

    // Search functionality
    const searchInput = document.querySelector('.search-input');
    const searchResults = document.querySelector('.search-results');
    let searchTimeout;

    if (searchInput) {
        // Handle input changes
        searchInput.addEventListener('input', handleSearch);

        // Handle enter key
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const firstResult = searchResults.querySelector('.search-result-item');
                if (firstResult) {
                    window.location.href = firstResult.href;
                }
            }
        });

        // Handle blur (clicking outside)
        document.addEventListener('click', function(e) {
            if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
                searchResults.classList.remove('active');
            }
        });
    }

    function handleSearch() {
        clearTimeout(searchTimeout);
        const query = searchInput.value.trim();

        if (query.length < 1) {
            searchResults.classList.remove('active');
            return;
        }

        searchTimeout = setTimeout(() => {
            fetch(`/search?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    searchResults.innerHTML = '';
                    if (data.length > 0) {
                        data.forEach(stock => {
                            const isPositive = stock.change >= 0;
                            searchResults.innerHTML += `
                                <a href="/stock/${stock.symbol}" class="search-result-item">
                                    <div class="search-result-left">
                                        <div class="search-result-symbol">${stock.symbol}</div>
                                    </div>
                                    <div class="search-result-right">
                                        <div class="search-result-price">$${stock.price.toFixed(2)}</div>
                                        <div class="search-result-change ${isPositive ? 'positive' : 'negative'}">
                                            ${isPositive ? '↑' : '↓'} ${Math.abs(stock.change).toFixed(2)}
                                            (${Math.abs(stock.percent_change).toFixed(2)}%)
                                        </div>
                                    </div>
                                </a>
                            `;
                        });
                    } else {
                        searchResults.innerHTML = '<div class="search-result-item">No results found</div>';
                    }
                    searchResults.classList.add('active');
                })
                .catch(error => {
                    console.error('Search error:', error);
                    searchResults.innerHTML = '<div class="search-result-item">Error fetching results</div>';
                    searchResults.classList.add('active');
                });
        }, 300);
    }

    // Real-time updates
    setInterval(() => {
        document.querySelectorAll('.stock-card').forEach(card => {
            const symbol = card.dataset.symbol;
            fetch(`/stock/${symbol}`)
                .then(response => response.json())
                .then(data => {
                    if (data && !data.error) {
                        updateStockCard(card, data);
                    }
                })
                .catch(error => console.error(`Error updating ${symbol}:`, error));
        });
    }, 5000);

    function updateStockCard(card, data) {
        const priceEl = card.querySelector('.stock-price');
        const changeEl = card.querySelector('.stock-change');
        const volumeEl = card.querySelector('.stock-volume');
        const canvas = card.querySelector('.stock-mini-chart');

        // Update price with animation
        const oldPrice = parseFloat(priceEl.textContent.replace('$', ''));
        const newPrice = data.price;
        priceEl.textContent = `$${newPrice.toFixed(2)}`;
        priceEl.classList.add(newPrice > oldPrice ? 'flash-green' : 'flash-red');

        // Update change
        changeEl.className = `stock-change ${data.change >= 0 ? 'positive' : 'negative'}`;
        changeEl.innerHTML = `${data.change >= 0 ? '↑' : '↓'} $${Math.abs(data.change).toFixed(2)} (${Math.abs(data.percent_change).toFixed(2)}%)`;

        // Update volume
        volumeEl.textContent = `Vol: ${data.volume}`;

        // Update chart
        if (canvas) {
            const ctx = canvas.getContext('2d');
            drawMiniChart(ctx, data.chart_data, data.change >= 0);
        }

        // Remove flash animation
        setTimeout(() => {
            priceEl.classList.remove('flash-green', 'flash-red');
        }, 1000);
    }

    // Make stock cards clickable
    document.querySelectorAll('.stock-card').forEach(card => {
        card.addEventListener('click', function(e) {
            if (!e.target.closest('.watchlist-form') && !e.target.closest('.remove-form')) {
                const symbol = this.dataset.symbol;
                window.location.href = `/stock/${symbol}`;
            }
        });
    });
});