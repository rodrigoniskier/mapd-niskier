import base64
from io import BytesIO

from django.http import HttpResponse
from django.utils import timezone


def qr_data_uri(texto):
    try:
        import qrcode

        imagem = qrcode.make(texto)
        buffer = BytesIO()
        imagem.save(buffer, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
    except Exception:
        return ""


def certificado_pdf_response(tentativa, validation_url):
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.pdfgen import canvas
        from reportlab.platypus import Paragraph
    except ImportError:
        return HttpResponse(
            "A dependência reportlab não está instalada. Execute pip install -r requirements.txt.",
            status=503,
            content_type="text/plain; charset=utf-8",
        )

    buffer = BytesIO()
    pagina = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=pagina)
    largura, altura = pagina

    c.setFillColor(colors.HexColor("#F7F9FC"))
    c.rect(0, 0, largura, altura, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor("#173B65"))
    c.setLineWidth(4)
    c.rect(1.2 * cm, 1.2 * cm, largura - 2.4 * cm, altura - 2.4 * cm, fill=0, stroke=1)

    c.setFillColor(colors.HexColor("#173B65"))
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(largura / 2, altura - 3.2 * cm, "MAPD NISKIER")
    c.setFont("Helvetica", 12)
    c.drawCentredString(largura / 2, altura - 4.0 * cm, "Medicina — UNIPÊ")

    c.setFillColor(colors.HexColor("#1F2937"))
    c.setFont("Helvetica-Bold", 21)
    c.drawCentredString(largura / 2, altura - 5.7 * cm, "Comprovante de Conclusão de Atividade Formativa")

    estilos = getSampleStyleSheet()
    estilo = ParagraphStyle(
        "certificado",
        parent=estilos["BodyText"],
        fontName="Helvetica",
        fontSize=14,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1F2937"),
    )
    texto = (
        f"Certifica-se que <b>{tentativa.aluno.nome_exibicao}</b>, RGM "
        f"<b>{tentativa.aluno.rgm or tentativa.aluno.username}</b>, concluiu a atividade formativa "
        f"do tema <b>{tentativa.tema.titulo}</b>, obtendo nota <b>{tentativa.nota_total}/10,0</b>."
    )
    p = Paragraph(texto, estilo)
    w, h = p.wrap(largura - 8 * cm, 6 * cm)
    p.drawOn(c, 4 * cm, altura / 2 - h / 2)

    data = tentativa.concluida_em or timezone.now()
    c.setFont("Helvetica", 10)
    c.drawCentredString(largura / 2, 3.3 * cm, f"Concluído em {data:%d/%m/%Y às %H:%M}")
    c.drawCentredString(largura / 2, 2.7 * cm, f"Código de validação: {tentativa.codigo_comprovante}")
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(largura / 2, 2.1 * cm, validation_url)
    c.save()
    buffer.seek(0)
    resposta = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    resposta["Content-Disposition"] = (
        f'attachment; filename="comprovante-mapd-{tentativa.codigo_comprovante}.pdf"'
    )
    return resposta


def relatorio_pdf_response(tentativas, titulo="Relatório de desempenho"):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        return HttpResponse(
            "A dependência reportlab não está instalada.", status=503, content_type="text/plain; charset=utf-8"
        )

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.2 * cm, leftMargin=1.2 * cm)
    estilos = getSampleStyleSheet()
    elementos = [Paragraph(titulo, estilos["Title"]), Spacer(1, 0.4 * cm)]
    dados = [["Aluno", "RGM", "Turma", "Tema", "Nota", "Pistas", "Data"]]
    for t in tentativas:
        dados.append(
            [
                t.aluno.nome_exibicao,
                t.aluno.rgm or t.aluno.username,
                t.aluno.turma.codigo if t.aluno.turma else "—",
                t.tema.titulo,
                str(t.nota_total),
                str(t.quantidade_pistas),
                t.concluida_em.strftime("%d/%m/%Y") if t.concluida_em else "—",
            ]
        )
    tabela = Table(dados, repeatRows=1, colWidths=[3.2 * cm, 2.1 * cm, 1.3 * cm, 5.1 * cm, 1.2 * cm, 1.2 * cm, 2 * cm])
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173B65")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ]
        )
    )
    elementos.append(tabela)
    doc.build(elementos)
    buffer.seek(0)
    resposta = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    resposta["Content-Disposition"] = 'attachment; filename="relatorio-mapd.pdf"'
    return resposta
