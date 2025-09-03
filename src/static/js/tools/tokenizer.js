// GPT Tokenizer Tool
class GPTTokenizerTool {
    constructor() {
        this.tokenizers = {};
        this.currentModel = 'gpt-4o';
        this.init();
    }

    async init() {
        this.loadTokenizers();
        this.setupEventListeners();
        this.setupModelSelector();
    }

    loadTokenizers() {
        // Load different tokenizer encodings based on available globals
        if (typeof GPTTokenizer_o200k_base !== 'undefined') {
            this.tokenizers['o200k_base'] = GPTTokenizer_o200k_base;
        }
        if (typeof GPTTokenizer_cl100k_base !== 'undefined') {
            this.tokenizers['cl100k_base'] = GPTTokenizer_cl100k_base;
        }
        if (typeof GPTTokenizer_p50k_base !== 'undefined') {
            this.tokenizers['p50k_base'] = GPTTokenizer_p50k_base;
        }
    }

    getTokenizerForModel(model) {
        const modelEncodings = {
            'gpt-4o': 'o200k_base',
            'gpt-4': 'cl100k_base',
            'gpt-3.5-turbo': 'cl100k_base',
            'text-davinci-003': 'p50k_base'
        };
        
        const encoding = modelEncodings[model];
        return this.tokenizers[encoding];
    }

    setupEventListeners() {
        const textInput = document.getElementById('text-input');
        const modelSelect = document.getElementById('model-select');
        const analyzeChatBtn = document.getElementById('analyze-chat-btn');

        // Real-time analysis on text input
        textInput.addEventListener('input', () => {
            this.analyzeText();
        });

        // Model change
        modelSelect.addEventListener('change', (e) => {
            this.currentModel = e.target.value;
            this.analyzeText();
        });

        // Chat analysis
        analyzeChatBtn.addEventListener('click', () => {
            this.analyzeChat();
        });
    }

    setupModelSelector() {
        // Set initial model
        document.getElementById('model-select').value = this.currentModel;
    }

    analyzeText() {
        const text = document.getElementById('text-input').value;
        const tokenizer = this.getTokenizerForModel(this.currentModel);

        if (!tokenizer || !text.trim()) {
            this.clearResults();
            return;
        }

        try {
            // Basic text analysis
            const tokens = tokenizer.encode(text);
            const decodedText = tokenizer.decode(tokens);
            
            // Update basic stats
            this.updateBasicStats(text, tokens);
            
            // Update token visualization
            this.updateTokenVisualization(tokens, text);
            
            // Update cost estimation
            this.updateCostEstimation(tokens);

        } catch (error) {
            console.error('Error analyzing text:', error);
            this.showError('Error analyzing text. Please check your input.');
        }
    }

    updateBasicStats(text, tokens) {
        const charCount = text.length;
        const wordCount = text.trim().split(/\s+/).filter(word => word.length > 0).length;
        const tokenCount = tokens.length;

        document.getElementById('char-count').textContent = charCount.toLocaleString();
        document.getElementById('word-count').textContent = wordCount.toLocaleString();
        document.getElementById('token-count').textContent = tokenCount.toLocaleString();
    }

    updateTokenVisualization(tokens, originalText) {
        const tokenList = document.getElementById('token-list');
        const tokenizer = this.getTokenizerForModel(this.currentModel);
        
        if (tokens.length === 0) {
            tokenList.innerHTML = '<p class="placeholder-text">No tokens found</p>';
            return;
        }

        let html = '<div class="token-grid">';
        tokens.forEach((token, index) => {
            const decodedToken = tokenizer.decode([token]);
            const tokenClass = this.getTokenClass(decodedToken);
            
            html += `
                <div class="token-item ${tokenClass}" title="Token ${index + 1}: ${decodedToken}">
                    <span class="token-text">${this.escapeHtml(decodedToken)}</span>
                    <span class="token-id">${token}</span>
                </div>
            `;
        });
        html += '</div>';

        tokenList.innerHTML = html;
    }

    getTokenClass(decodedToken) {
        if (decodedToken.trim() === '') return 'token-whitespace';
        if (/^\s+$/.test(decodedToken)) return 'token-whitespace';
        if (/^[a-zA-Z]+$/.test(decodedToken)) return 'token-word';
        if (/^[0-9]+$/.test(decodedToken)) return 'token-number';
        if (/^[^\w\s]+$/.test(decodedToken)) return 'token-punctuation';
        return 'token-mixed';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    updateCostEstimation(tokens) {
        const costElement = document.getElementById('estimated-cost');
        const tokenCount = tokens.length;
        
        // Rough cost estimates (these are approximate and may vary)
        const costEstimates = {
            'gpt-4o': { input: 0.0025, output: 0.01 }, // per 1K tokens
            'gpt-4': { input: 0.03, output: 0.06 },
            'gpt-3.5-turbo': { input: 0.0015, output: 0.002 },
            'text-davinci-003': { input: 0.02, output: 0.02 }
        };

        const model = this.currentModel;
        const estimates = costEstimates[model];
        
        if (estimates) {
            const inputCost = (tokenCount / 1000) * estimates.input;
            const outputCost = (tokenCount / 1000) * estimates.output;
            const totalCost = inputCost + outputCost;
            
            costElement.innerHTML = `
                <div class="cost-breakdown">
                    <div>Input: $${inputCost.toFixed(4)}</div>
                    <div>Output: $${outputCost.toFixed(4)}</div>
                    <div class="total-cost">Total: $${totalCost.toFixed(4)}</div>
                </div>
            `;
        } else {
            costElement.textContent = 'N/A';
        }
    }

    analyzeChat() {
        const chatInput = document.getElementById('chat-input').value;
        const chatResults = document.getElementById('chat-results');
        const chatStats = document.getElementById('chat-stats');

        if (!chatInput.trim()) {
            this.showError('Please enter chat messages to analyze.');
            return;
        }

        try {
            const messages = JSON.parse(chatInput);
            if (!Array.isArray(messages)) {
                throw new Error('Chat must be an array of messages');
            }

            const tokenizer = this.getTokenizerForModel(this.currentModel);
            if (!tokenizer) {
                this.showError('Tokenizer not available for selected model.');
                return;
            }

            let totalTokens = 0;
            let userTokens = 0;
            let assistantTokens = 0;
            let systemTokens = 0;

            messages.forEach(message => {
                if (!message.role || !message.content) {
                    throw new Error('Each message must have role and content');
                }

                const tokens = tokenizer.encode(message.content);
                totalTokens += tokens.length;

                switch (message.role) {
                    case 'user':
                        userTokens += tokens.length;
                        break;
                    case 'assistant':
                        assistantTokens += tokens.length;
                        break;
                    case 'system':
                        systemTokens += tokens.length;
                        break;
                }
            });

            // Display results
            chatStats.innerHTML = `
                <div class="chat-stat-grid">
                    <div class="chat-stat">
                        <h4>Total Messages</h4>
                        <span>${messages.length}</span>
                    </div>
                    <div class="chat-stat">
                        <h4>Total Tokens</h4>
                        <span>${totalTokens.toLocaleString()}</span>
                    </div>
                    <div class="chat-stat">
                        <h4>User Tokens</h4>
                        <span>${userTokens.toLocaleString()}</span>
                    </div>
                    <div class="chat-stat">
                        <h4>Assistant Tokens</h4>
                        <span>${assistantTokens.toLocaleString()}</span>
                    </div>
                    ${systemTokens > 0 ? `
                    <div class="chat-stat">
                        <h4>System Tokens</h4>
                        <span>${systemTokens.toLocaleString()}</span>
                    </div>
                    ` : ''}
                </div>
            `;

            chatResults.style.display = 'block';

        } catch (error) {
            console.error('Error analyzing chat:', error);
            this.showError('Error parsing chat messages. Please check the JSON format.');
        }
    }

    clearResults() {
        document.getElementById('token-count').textContent = '-';
        document.getElementById('char-count').textContent = '-';
        document.getElementById('word-count').textContent = '-';
        document.getElementById('estimated-cost').textContent = '-';
        document.getElementById('token-list').innerHTML = '<p class="placeholder-text">Tokens will appear here...</p>';
    }

    showError(message) {
        // Simple error display - you could enhance this with a toast notification
        console.error(message);
        alert(message);
    }
}

// Initialize the tool when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new GPTTokenizerTool();
}); 