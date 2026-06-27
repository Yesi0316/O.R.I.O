function formatReportTime(fechaStr) {
  if (!fechaStr) return '';
  const fecha = new Date(fechaStr);
  if (Number.isNaN(fecha.getTime())) return fechaStr;

  const ahora = new Date();
  const diff = ahora - fecha;
  const minutos = Math.floor(diff / 60000);

  if (minutos < 1) return 'Hace unos segundos';
  if (minutos < 60) return `Hace ${minutos} minuto${minutos === 1 ? '' : 's'}`;

  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `Hace ${horas} hora${horas === 1 ? '' : 's'}`;

  const dias = Math.floor(horas / 24);
  return `Hace ${dias} día${dias === 1 ? '' : 's'}`;
}

function normalizeReport(report) {
  const tipo = (report.tipo || report.TIPO || '').toString().toLowerCase();
  const title = report.NOMBRE || report.nombre || report.titulo || 'Sin nombre';
  const image = report.IMAGEN || report.imagen || report.Imagen || '';
  const color = report.COLOR || report.color || '';
  const category = report.nombre_categoria || report.CATEGORIA || report.categoria || '';
  const location = report.LUGAR || report.lugar || report.UBICACION || report.ubicacion || category || 'Ubicación no disponible';
  const date = report.FECHA || report.fecha || report.Fecha || '';
  const id = report.ID_OBJETO || report.id_objeto || report.ID_REPORTE || report.id_reporte || report.ID_REPORTE_ENC || report.id_reporte_enc || report.id || '';
  const user = report.NOMBRE_USUARIO || report.nombre_usuario || report.user || report.usuario || report.autor || 'Usuario';
  const reportId = report.ID_REPORTE || report.id_reporte || report.ID_REPORTE_ENC || report.id_reporte_enc || '';

  return {
    tipo,
    title,
    image,
    color,
    category,
    location,
    date,
    id,
    user,
    reportId,
    raw: report,
  };
}

function buildReportCardHtml(report, options = {}) {
  const r = normalizeReport(report);
  const estado = r.tipo === 'encontrado' ? 'Encontrado' : 'Perdido';
  const estadoClass = r.tipo === 'encontrado' ? 'status-found' : 'status-lost';
  const fechaTexto = formatReportTime(r.date);
  const imageUrl = r.image || '/static/img/image.png';
  const userName = options.userName || r.user;
  const href = options.clickable && !options.showDeleteButton ? `/detalles/${r.id}` : '';
  const wrapperTag = href ? 'a' : 'div';
  const wrapperAttrs = href ? `href="${href}"` : `data-detail-href="/detalles/${r.id}"`;
  const deleteButton = options.showDeleteButton
    ? `<button type="button" class="report-card-delete" data-report-id="${r.reportId}" data-report-type="${r.tipo}">Eliminar</button>`
    : '';

  return `
    <${wrapperTag} class="report-card" ${wrapperAttrs}>
      <div class="report-card-header">
        <span class="report-status ${estadoClass}">${estado}</span>
        <span class="report-time">${fechaTexto}</span>
      </div>
      <h3 class="report-card-title">${r.title}</h3>
      <p class="report-card-location"><i class="fas fa-map-marker-alt"></i> ${r.location}</p>
      <div class="report-card-image" style="background-image: url('${imageUrl}');"></div>
      <div class="report-card-footer">
        <div class="user-chip"><i class="fas fa-user"></i></div>
        <span class="report-user">${userName}</span>
        ${deleteButton ? `<div class="report-card-actions">${deleteButton}</div>` : ''}
      </div>
    </${wrapperTag}>
  `;
}

function renderReportCards(container, reports, options = {}) {
  if (!container) return;
  container.innerHTML = '';

  if (!Array.isArray(reports) || reports.length === 0) {
    const message = options.emptyMessage || 'No hay reportes para mostrar.';
    container.innerHTML = `<div class="recent-placeholder">${message}</div>`;
    return;
  }

  reports.forEach(report => {
    container.insertAdjacentHTML('beforeend', buildReportCardHtml(report, options));
  });

  if (options.onDelete) {
    container.querySelectorAll('.report-card-delete').forEach(button => {
      button.addEventListener('click', event => {
        event.stopPropagation();
        const id = button.dataset.reportId;
        const tipo = button.dataset.reportType;
        if (id) options.onDelete(id, tipo);
      });
    });
  }

  if (options.onCardClick) {
    container.querySelectorAll('.report-card[data-detail-href]').forEach(card => {
      card.addEventListener('click', event => {
        if (event.target.closest('.report-card-delete')) return;
        const href = card.dataset.detailHref;
        if (href) options.onCardClick(href, card);
      });
    });
  }
}
