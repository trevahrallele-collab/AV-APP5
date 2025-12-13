import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.offline as pyo

class StockPlotter:
    @staticmethod
    def plot_data(df, filename):
        plt.figure(figsize=(12, 6))
        plt.plot(df.index, df['close'], label='Close Price')
        plt.title('Stock Price')
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.legend()
        plt.savefig(filename)
        plt.close()
    
    @staticmethod
    def plot_candlestick(df, filename):
        fig, ax = plt.subplots(figsize=(12, 6))
        for i, (date, row) in enumerate(df.iterrows()):
            color = 'green' if row['close'] >= row['open'] else 'red'
            ax.plot([i, i], [row['low'], row['high']], color='black', linewidth=1)
            ax.plot([i, i], [row['open'], row['close']], color=color, linewidth=3)
        ax.set_title('Candlestick Chart')
        plt.savefig(filename)
        plt.close()
    
    @staticmethod
    def plot_interactive(df, filename):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['close'], name='Close Price'))
        fig.update_layout(title='Interactive Stock Price', xaxis_title='Date', yaxis_title='Price')
        pyo.plot(fig, filename=filename, auto_open=False)
    
    @staticmethod
    def plot_interactive_candlestick(df, filename):
        fig = go.Figure(data=go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close']
        ))
        fig.update_layout(title='Interactive Candlestick Chart')
        pyo.plot(fig, filename=filename, auto_open=False)