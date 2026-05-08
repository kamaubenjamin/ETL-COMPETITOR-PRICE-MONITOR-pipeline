"""
Reporting module for generating CSV and PDF reports of workflow results.
"""
import pandas as pd
import os
from datetime import datetime
from typing import Dict, List, Optional

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.units import inch
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


class WorkflowReporter:
    """Generates reports from workflow execution results."""

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def export_comparison_csv(
        self,
        comparison_df: pd.DataFrame,
        workflow_name: str,
        timestamp: Optional[str] = None,
    ) -> str:
        """Export price comparison to CSV."""
        timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(
            self.output_dir,
            f"comparison_{workflow_name.replace(' ', '_')}_{timestamp}.csv"
        )
        
        comparison_df.to_csv(filename, index=False)
        return filename

    def export_alerts_csv(
        self,
        alerts: List[str],
        workflow_name: str,
        timestamp: Optional[str] = None,
    ) -> str:
        """Export alerts to CSV."""
        timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(
            self.output_dir,
            f"alerts_{workflow_name.replace(' ', '_')}_{timestamp}.csv"
        )
        
        df = pd.DataFrame({
            'timestamp': [datetime.now().isoformat()] * len(alerts),
            'alert': alerts,
        })
        
        df.to_csv(filename, index=False)
        return filename

    def export_comparison_pdf(
        self,
        comparison_df: pd.DataFrame,
        workflow_name: str,
        timestamp: Optional[str] = None,
    ) -> Optional[str]:
        """Export price comparison to PDF."""
        if not HAS_REPORTLAB:
            return None

        timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(
            self.output_dir,
            f"comparison_{workflow_name.replace(' ', '_')}_{timestamp}.pdf"
        )

        pdf = SimpleDocTemplate(filename, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        title = Paragraph(
            f"<b>Price Comparison Report: {workflow_name}</b>",
            styles['Heading1']
        )
        story.append(title)

        timestamp_text = Paragraph(
            f"<i>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>",
            styles['Normal']
        )
        story.append(timestamp_text)
        story.append(Spacer(1, 0.3 * inch))

        columns = list(comparison_df.columns)
        data = [columns] + comparison_df.values.tolist()

        table = Table(data, colWidths=[2*inch if col == 'product_name' else 1.2*inch for col in columns])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))

        story.append(table)

        try:
            pdf.build(story)
            return filename
        except Exception:
            return None

    def export_alerts_pdf(
        self,
        alerts: List[str],
        workflow_name: str,
        timestamp: Optional[str] = None,
    ) -> Optional[str]:
        """Export alerts to PDF."""
        if not HAS_REPORTLAB:
            return None

        timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(
            self.output_dir,
            f"alerts_{workflow_name.replace(' ', '_')}_{timestamp}.pdf"
        )

        pdf = SimpleDocTemplate(filename, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        title = Paragraph(
            f"<b>Price Alerts Report: {workflow_name}</b>",
            styles['Heading1']
        )
        story.append(title)

        timestamp_text = Paragraph(
            f"<i>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>",
            styles['Normal']
        )
        story.append(timestamp_text)
        story.append(Spacer(1, 0.3 * inch))

        alert_count = Paragraph(
            f"<b>Total Alerts: {len(alerts)}</b>",
            styles['Heading2']
        )
        story.append(alert_count)
        story.append(Spacer(1, 0.2 * inch))

        for alert in alerts:
            if alert.startswith("No"):
                continue
            alert_text = Paragraph(f"• {alert}", styles['Normal'])
            story.append(alert_text)
            story.append(Spacer(1, 0.1 * inch))

        try:
            pdf.build(story)
            return filename
        except Exception:
            return None

    def generate_summary(
        self,
        comparison_df: pd.DataFrame,
        alerts: List[str],
        workflow_name: str,
    ) -> Dict:
        """Generate a summary of workflow results."""
        return {
            'workflow': workflow_name,
            'timestamp': datetime.now().isoformat(),
            'products_compared': len(comparison_df),
            'total_alerts': len(alerts),
            'price_differences': comparison_df[
                [col for col in comparison_df.columns if col != 'product_name' and col != 'cheapest']
            ].notna().sum().sum(),
        }


# Global reporter instance
reporter = WorkflowReporter()
