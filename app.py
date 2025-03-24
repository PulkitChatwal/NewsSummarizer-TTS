import gradio as gr
from utils import generate_report

with gr.Blocks() as app:
    gr.Markdown("# 📰 News Analyzer")
    company = gr.Textbox(label="Company Name", placeholder="e.g., Apple, Tesla, Reliance")
    btn = gr.Button("Analyze News")
    
    with gr.Row():
        report = gr.JSON(label="Analysis Report")
        audio = gr.Audio(label="Hindi Summary", visible=False)
    
    def analyze(company):
        if not company.strip():
            return {"error": "Please enter a company name"}, gr.Audio(visible=False)
        
        report, audio_path = generate_report(company.strip())
        return report, gr.Audio(audio_path, visible=True) if audio_path else (report, gr.Audio(visible=False))
    
    btn.click(analyze, inputs=company, outputs=[report, audio])

if __name__ == "__main__":
    app.launch()