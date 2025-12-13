import dash
from dash import dcc, html
import plotly.graph_objects as go
from av_data_fetcher import AVDataFetcher

def create_dash_app():
    app = dash.Dash(__name__)
    
    API_KEY = "74M88OXCGWTNUIV9"
    
    try:
        fetcher = AVDataFetcher(API_KEY)
        df = fetcher.load_from_db()
        
        if df is None or df.empty:
            df = fetcher.fetch_daily_data("AAPL")
            fetcher.save_to_csv(df)
            fetcher.save_to_db(df)
        
        # Line chart
        line_fig = go.Figure()
        line_fig.add_trace(go.Scatter(
            x=df.index, 
            y=df['close'], 
            mode='lines', 
            name='Close Price',
            line=dict(width=2, color='#1f77b4')
        ))
        line_fig.update_layout(
            title="Stock Price Over Time",
            xaxis_title="Date",
            yaxis_title="Price ($)",
            template="plotly_white",
            height=500
        )
        
        # Candlestick chart
        candlestick_fig = go.Figure(data=go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close']
        ))
        candlestick_fig.update_layout(
            title="Candlestick Chart",
            xaxis_title="Date",
            yaxis_title="Price ($)",
            template="plotly_white",
            height=500
        )
        
    except Exception as e:
        # Create empty figures on error
        line_fig = go.Figure()
        line_fig.add_annotation(text=f"Error loading data: {str(e)}", 
                               xref="paper", yref="paper", x=0.5, y=0.5)
        candlestick_fig = go.Figure()
        candlestick_fig.add_annotation(text=f"Error loading data: {str(e)}", 
                                      xref="paper", yref="paper", x=0.5, y=0.5)
    
    app.layout = html.Div([
        html.H1("📈 Market Data Visualization", 
                style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '30px'}),
        
        html.Div([
            html.H2("📊 Line Chart", style={'textAlign': 'center', 'color': '#34495e'}),
            dcc.Graph(figure=line_fig)
        ], style={'marginBottom': '40px'}),
        
        html.Div([
            html.H2("🕯️ Candlestick Chart", style={'textAlign': 'center', 'color': '#34495e'}),
            dcc.Graph(figure=candlestick_fig)
        ]),
        
        html.Div([
            html.A("📈 Interactive Line Chart", 
                   href="/interactive", 
                   style={'margin': '10px', 'padding': '10px 20px', 
                         'backgroundColor': '#3498db', 'color': 'white',
                         'textDecoration': 'none', 'borderRadius': '5px'}),
            html.A("🕯️ Interactive Candlestick", 
                   href="/interactive-candlestick",
                   style={'margin': '10px', 'padding': '10px 20px',
                         'backgroundColor': '#e74c3c', 'color': 'white', 
                         'textDecoration': 'none', 'borderRadius': '5px'})
        ], style={'textAlign': 'center', 'marginTop': '30px'})
    ], style={'padding': '20px'})
    
    return app

if __name__ == '__main__':
    app = create_dash_app()
    app.run(debug=True, host='0.0.0.0', port=8081)