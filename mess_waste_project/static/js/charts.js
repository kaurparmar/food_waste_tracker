// Draws the report charts from the JSON API (/api/reports/<name>) using Chart.js
const CHARTS = [
  {name: 'waste_per_dish', canvas: 'chart-dish', label: r => r.name, value: r => r.total_wasted_kg, title: 'Wasted kg', type: 'bar', color: '#0f7b6c'},
  {name: 'waste_by_meal', canvas: 'chart-meal', label: r => r.meal_type, value: r => r.waste_percent, title: 'Waste %', type: 'bar', color: '#be185d'},
  {name: 'money_lost', canvas: 'chart-money', label: r => r.year + '-W' + r.week, value: r => r.money_lost, title: 'Rupees lost', type: 'line', color: '#be185d'},
  {name: 'ratings', canvas: 'chart-ratings', label: r => r.name, value: r => r.avg_rating, title: 'Average rating', type: 'bar', color: '#2a9d8f'},
  {name: 'waste_by_block', canvas: 'chart-block', label: r => 'Block ' + r.block, value: r => r.wasted_kg, title: 'Wasted kg', type: 'bar', color: '#264653'}
];

CHARTS.forEach(cfg => {
  const el = document.getElementById(cfg.canvas);
  if (!el || typeof Chart === 'undefined') return;   // tables still work without charts
  fetch('/api/reports/' + cfg.name)
    .then(r => r.json())
    .then(rows => {  
      new Chart(el, {
        type: cfg.type,
        data: {labels: rows.map(cfg.label),
               datasets: [{label: cfg.title, data: rows.map(cfg.value),
                           backgroundColor: cfg.color, borderColor: cfg.color}]},
        options: {responsive: true, plugins: {legend: {display: false}}}
      });
    });
});
