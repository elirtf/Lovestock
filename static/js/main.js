// static/js/main.js

// Search Handler
class SearchHandler {
    constructor() {
        this.searchInput = document.querySelector('#stock-search');
        this.searchResults = document.querySelector('.search-results');
        this.searchTimeout = null;
        this.currentSearch = null;
        this.init();
    }

    init() {
        if (!this.searchInput || !this.searchResults) {
            console.error('Search elements not found');
            return;
        }

        console.log('Initializing search handler');

        this.searchInput.addEventListener('input', (e) => {
            clearTimeout(this.searchTimeout);
            const query = e.target.value.trim();

            if (query.length < 1) {
                this.hideResults();
                return;
            }

            this.showLoading();
            this.searchTimeout = setTimeout(() => this.performSearch(query), 300);
        });

        this.searchInput.addEventListener('focus', () => {
            if (this.searchInput.value.trim().length > 0) {
                this.performSearch(this.searchInput.value.trim());
            }
        });

        this.searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && this.searchInput.value.trim()) {
                const firstResult = this.searchResults.querySelector('.search-result-item');
                if (firstResult) {
                    window.location.href = firstResult.href;
                }
            }
        });

        document.addEventListener('click', (e) => {
            if (!this.searchInput.contains(e.target) && !this.searchResults.contains(e.target)) {
                this.hideResults();
            }
        });
    }

    showLoading() {
        this.searchResults.classList.add('active');
        this.searchResults.innerHTML = `
            <div class="search-loading">
                <span>Searching...</span>
                <div class="search-spinner"></div>
            </div>
        `;
    }

    async performSearch(query) {
        console.log('Performing search for:', query);

        if (this.currentSearch) {
            this.currentSearch.abort();
        }

        this.currentSearch = new AbortController();

        try {
            const response = await fetch(`/search?q=${encodeURIComponent(query)}`, {
                signal: this.currentSearch.signal
            });

            if (!response.ok) {
                throw new Error(`Search failed: ${response.statusText}`);
            }

            const results = await response.json();
            console.log('Search results:', results);

            if (results.error) {
                throw new Error(results.error);
            }

            this.displayResults(results);
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('Search aborted');
                return;
            }

            console.error('Search error:', error);
            this.searchResults.innerHTML = `
                <div class="search-result-item">
                    <div class="search-error">
                        ${error.message || 'Error performing search'}
                    </div>
                </div>
            `;
        }
    }

    displayResults(results) {
        if (!Array.isArray(results) || results.length === 0) {
            this.searchResults.innerHTML = `
                <div class="search-result-item">
                    <div class="search-result-message">
                        No results found
                    </div>
                </div>
            `;
            return;
        }

        this.searchResults.innerHTML = results.map(result => {
            const changeClass = result.change >= 0 ? 'positive' : 'negative';
            const changeSign = result.change >= 0 ? '+' : '';

            return `
                <a href="/stock/${result.symbol}" class="search-result-item">
                    <div class="search-result-left">
                        <span class="search-result-symbol">${result.symbol}</span>
                        <span class="search-result-updated">Updated: ${result.updated_at}</span>
                    </div>
                    <div class="search-result-right">
                        <div class="search-result-price">$${result.price}</div>
                        <div class="search-result-change ${changeClass}">
                            ${changeSign}${result.change} (${result.percent_change}%)
                        </div>
                    </div>
                </a>
            `;
        }).join('');
    }

    hideResults() {
        this.searchResults.classList.remove('active');
    }
}

class StockDetailChart {
    constructor() {
        this.container = document.querySelector('.stock-chart-container');
        if (this.container) {
            this.init();
        }
    }

    init() {
        const ctx = this.container.querySelector('canvas')?.getContext('2d');
        if (!ctx) return;

        // Get the stock data from the page
        const histData = JSON.parse(this.container.dataset.history || '[]');
        if (!histData.length) return;

        const prices = histData.map(d => d.Close);
        const labels = histData.map(d => new Date(d.Date).toLocaleTimeString());

        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Price',
                    data: prices,
                    borderColor: '#2563eb',
                    borderWidth: 2,
                    tension: 0.4,
                    pointRadius: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: true,
                        callbacks: {
                            label: function(context) {
                                return `$${context.raw.toFixed(2)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        display: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        },
                        ticks: {
                            callback: function(value) {
                                return `$${value.toFixed(2)}`;
                            }
                        }
                    }
                }
            }
        });
    }
}

// Stock update handling
class StockUpdater {
    constructor() {
        this.updateInterval = 5000; // 5 seconds
        this.charts = new Map();
        this.initialized = false;
        console.log('StockUpdater constructed');
    }

    init() {
        if (this.initialized) return;
        this.initialized = true;
        console.log('StockUpdater initializing...');

        // Initialize all stock cards on the page
        const cards = document.querySelectorAll('.stock-card');
        console.log('Found stock cards:', cards.length);

        cards.forEach(card => {
            const symbol = card.dataset.symbol;  // Changed from getAttribute('symbol')
            console.log('Processing card for symbol:', symbol);

            if (symbol) {
                this.initializeChart(card, symbol);
                this.updateStockCard(symbol);
            }
        });

        // Start update loop
        this.startUpdateLoop();
        console.log('Update loop started');
    }

    initializeChart(card, symbol) {
        console.log('Initializing chart for:', symbol);
        const canvas = card.querySelector('.stock-mini-chart');

        if (!canvas) {
            console.log('No canvas found for:', symbol);
            return;
        }

        try {
            const ctx = canvas.getContext('2d');
            console.log('Got context for:', symbol);

            const chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: Array(100).fill(''),
                    datasets: [{
                        data: Array(100).fill(0),
                        borderColor: '#2563eb',
                        borderWidth: 1,
                        tension: 0.4,
                        pointRadius: 0,
                        fill: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: { display: false },
                        y: {
                            display: false,
                            beginAtZero: false
                        }
                    },
                    animation: false,
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    layout: {
                        padding: {
                            top: 5,
                            bottom: 5
                        }
                    },
                    elements: {
                        line: {
                            tension: 0.4
                        }
                    }
                }
            });

            this.charts.set(symbol, chart);
            console.log('Chart created for:', symbol);
        } catch (error) {
            console.error('Error creating chart for ' + symbol + ':', error);
        }
    }

    async updateStockCard(symbol) {
        console.log('Updating stock card:', symbol);
        try {
            const response = await fetch(`/api/stock/${symbol}/latest`);
            if (!response.ok) throw new Error('Network response was not ok');
            const data = await response.json();
            console.log('Received data for:', symbol, data);

            // Find all cards for this symbol (main list and watchlist)
            document.querySelectorAll(`.stock-card[data-symbol="${symbol}"]`).forEach(card => {
                // Update price
                const priceElement = card.querySelector('.stock-price');
                if (priceElement) {
                    priceElement.textContent = `$${data.price}`;
                }

                // Update change
                const changeElement = card.querySelector('.stock-change');
                if (changeElement) {
                    const sign = data.change >= 0 ? '+' : '';
                    changeElement.textContent = `${sign}${data.change} (${data.percent_change}%)`;
                    changeElement.className = `stock-change ${data.change >= 0 ? 'positive' : 'negative'}`;
                }

                // Update timestamp
                const timestampElement = card.querySelector('.timestamp');
                if (timestampElement) {
                    timestampElement.textContent = `Updated: ${data.updated_at}`;
                }

                // Update chart if it exists
                const chart = this.charts.get(symbol);
                if (chart && data.chart_data) {
                    console.log('Updating chart data for:', symbol);
                    chart.data.datasets[0].data = data.chart_data;
                    chart.update('none');
                }
            });
        } catch (error) {
            console.error(`Error updating ${symbol}:`, error);
        }
    }

    async startUpdateLoop() {
        while (true) {
            console.log('Update loop iteration starting');
            const cards = document.querySelectorAll('.stock-card');
            for (const card of cards) {
                const symbol = card.dataset.symbol;  // Changed from getAttribute('symbol')
                if (symbol) {
                    await this.updateStockCard(symbol);
                }
            }
            await new Promise(resolve => setTimeout(resolve, this.updateInterval));
        if (Promise.error) {
            throw new Error(Promise.error);
        }}
    }
}

// Update your DOM loaded event listener
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing components');
    // Initialize stock updater
    const stockUpdater = new StockUpdater();
    stockUpdater.init();
    // Initialize search
    const searchHandler = new SearchHandler();
    // Initialize detail chart if on detail page
    const detailChart = new StockDetailChart();
});