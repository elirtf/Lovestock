// static/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    // Search functionality
    const searchInput = document.querySelector('.search-input');
    const searchResults = document.querySelector('.search-results');
    let searchTimeout;

    if (searchInput) {
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();

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
        });

        // Close search results when clicking outside
        document.addEventListener('click', function(e) {
            if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
                searchResults.classList.remove('active');
            }
        });
    }
});