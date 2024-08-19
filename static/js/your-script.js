document.addEventListener('DOMContentLoaded', function() {
    const ctx = document.getElementById('myChart').getContext('2d');

    function fetchDataAndCreateChart() {
        fetch('/get_chart_data')
            .then(response => response.json())
            .then(data => {
                const config = {
                    type: 'bar',
                    data: {
                        labels: ['All Time', 'Last 3 Months', 'Last Month', 'Last Week'],
                        datasets: [
                            {
                                label: 'Buyins',
                                data: [data.all_time.buyins, data.last_3_months.buyins, data.last_month.buyins, data.last_week.buyins],
                                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                                borderColor: 'rgb(255, 99, 132)',
                                borderWidth: 1
                            },
                            {
                                label: 'Cashouts',
                                data: [data.all_time.cashouts, data.last_3_months.cashouts, data.last_month.cashouts, data.last_week.cashouts],
                                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                                borderColor: 'rgb(75, 192, 192)',
                                borderWidth: 1
                            },
                            {
                                label: 'Net Profit',
                                data: [data.all_time.net_profits, data.last_3_months.net_profits, data.last_month.net_profits, data.last_week.net_profits],
                                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                                borderColor: 'rgb(54, 162, 235)',
                                borderWidth: 1
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: {
                                position: 'top',
                                labels: {
                                    boxWidth: 40,
                                    padding: 20
                                },
                                padding: {
                                    bottom: 100 // This creates space between the legend and the chart
                                }
                            },
                        },
                        scales: {
                            x: {
                                ticks: {
                                    padding: 10 // Adjusts the distance of the x-axis labels from the chart
                                }
                            },
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    padding: 10 // Adjusts the distance of the y-axis labels from the chart
                                }
                            }
                        }
                    }
                };

                new Chart(ctx, config);
            })
            .catch(error => console.error('Error fetching data:', error));
    }

    fetchDataAndCreateChart();
});

