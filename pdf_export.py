from reportlab.platypus import SimpleDocTemplate, Table

def export_pdf(bookings, filename="estate.pdf"):

    doc = SimpleDocTemplate(filename)

    data = [["Nome", "Inizio", "Fine"]]

    for b in bookings:
        data.append([b[1], b[2], b[3]])

    table = Table(data)
    doc.build([table])
