document.addEventListener("DOMContentLoaded", function() {
    // 1. Weather Form Validation & Auto-calculators
    const form = document.getElementById("flood-prediction-form");
    if (form) {
        // Inputs
        const temp = document.getElementById("Temp");
        const humidity = document.getElementById("Humidity");
        const cloudCover = document.getElementById("Cloud Cover");
        const annual = document.getElementById("ANNUAL");
        const janFeb = document.getElementById("Jan-Feb");
        const marMay = document.getElementById("Mar-May");
        const junSep = document.getElementById("Jun-Sep");
        const octDec = document.getElementById("Oct-Dec");
        const avgJune = document.getElementById("avgjune");
        const sub = document.getElementById("sub");
        
        // Auto-calculator for Annual Rainfall
        const seasonalInputs = [janFeb, marMay, junSep, octDec];
        seasonalInputs.forEach(input => {
            if (input) {
                input.addEventListener("input", function() {
                    const jf = parseFloat(janFeb.value) || 0;
                    const mm = parseFloat(marMay.value) || 0;
                    const js = parseFloat(junSep.value) || 0;
                    const od = parseFloat(octDec.value) || 0;
                    // Auto populate ANNUAL if the user hasn't explicitly locked it
                    if (annual && !annual.dataset.userEdited) {
                        annual.value = (jf + mm + js + od).toFixed(1);
                    }
                });
            }
        });
        
        if (annual) {
            annual.addEventListener("input", function() {
                annual.dataset.userEdited = "true";
            });
        }

        form.addEventListener("submit", function(event) {
            let isValid = true;
            const errors = [];
            
            // Clean up previous alert
            const oldAlert = document.getElementById("validation-error-alert");
            if (oldAlert) oldAlert.remove();
            
            // Temperature Check (Typical ranges 20 to 45)
            const tVal = parseFloat(temp.value);
            if (isNaN(tVal) || tVal < 0 || tVal > 60) {
                isValid = false;
                errors.push("Temperature must be a realistic value between 0°C and 60°C.");
            }
            
            // Humidity Check (0 - 100)
            const hVal = parseFloat(humidity.value);
            if (isNaN(hVal) || hVal < 0 || hVal > 100) {
                isValid = false;
                errors.push("Humidity must be a percentage between 0% and 100%.");
            }
            
            // Cloud Cover Check (0 - 100)
            const cVal = parseFloat(cloudCover.value);
            if (isNaN(cVal) || cVal < 0 || cVal > 100) {
                isValid = false;
                errors.push("Cloud Cover must be a percentage between 0% and 100%.");
            }
            
            // Rainfall values non-negative
            const rainVals = {
                "Annual Rainfall": parseFloat(annual.value),
                "Jan-Feb Rainfall": parseFloat(janFeb.value),
                "Mar-May Rainfall": parseFloat(marMay.value),
                "Jun-Sep Rainfall": parseFloat(junSep.value),
                "Oct-Dec Rainfall": parseFloat(octDec.value),
                "Average June Rainfall": parseFloat(avgJune.value),
                "Sub-division Rainfall": parseFloat(sub.value)
            };
            
            for (const [name, val] of Object.entries(rainVals)) {
                if (isNaN(val) || val < 0) {
                    isValid = false;
                    errors.push(`${name} must be a valid non-negative rainfall amount (mm).`);
                }
            }
            
            // Check if seasonal sums roughly equal Annual (within 15%)
            const seasonalSum = (parseFloat(janFeb.value) || 0) + 
                                (parseFloat(marMay.value) || 0) + 
                                (parseFloat(junSep.value) || 0) + 
                                (parseFloat(octDec.value) || 0);
            const annVal = parseFloat(annual.value) || 0;
            if (annVal > 0 && Math.abs(annVal - seasonalSum) / annVal > 0.15) {
                // We show a confirmation/warning but don't strictly block unless they reject
                const confirmProceed = confirm(
                    `Annual Rainfall (${annVal} mm) differs from the sum of seasons (${seasonalSum.toFixed(1)} mm) by more than 15%.\n\nDo you want to proceed with these values?`
                );
                if (!confirmProceed) {
                    isValid = false;
                    event.preventDefault();
                    return;
                }
            }

            if (!isValid) {
                event.preventDefault();
                // Render error panel
                const alertDiv = document.createElement("div");
                alertDiv.id = "validation-error-alert";
                alertDiv.className = "alert alert-danger alert-dismissible fade show mb-4";
                alertDiv.role = "alert";
                alertDiv.innerHTML = `
                    <h5 class="alert-heading"><i class="fas fa-exclamation-triangle me-2"></i>Please Correct Form Errors</h5>
                    <ul class="mb-0 ps-3">
                        ${errors.map(err => `<li>${err}</li>`).join("")}
                    </ul>
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                `;
                form.prepend(alertDiv);
                window.scrollTo({ top: form.offsetTop - 100, behavior: 'smooth' });
            }
        });
    }

    // 2. Prediction Contribution Chart (attributions)
    const chartCanvas = document.getElementById("contributionChart");
    if (chartCanvas) {
        // Read dataset attribute
        const chartDataRaw = chartCanvas.dataset.contributions;
        if (chartDataRaw) {
            try {
                const contribs = JSON.parse(chartDataRaw);
                
                // Sort by contribution magnitude
                const sortedKeys = Object.keys(contribs).sort((a, b) => Math.abs(contribs[b]) - Math.abs(contribs[a]));
                
                const labels = [];
                const dataValues = [];
                const backgroundColors = [];
                const borderColors = [];
                
                // Map friendly display names
                const friendlyNames = {
                    'Temp': 'Temperature',
                    'Humidity': 'Humidity',
                    'Cloud Cover': 'Cloud Cover',
                    'ANNUAL': 'Annual Rainfall',
                    'Jan-Feb': 'Winter Rain (Jan-Feb)',
                    'Mar-May': 'Spring Rain (Mar-May)',
                    'Jun-Sep': 'Monsoon Rain (Jun-Sep)',
                    'Oct-Dec': 'Post-Monsoon Rain (Oct-Dec)',
                    'avgjune': 'Average June Rain',
                    'sub': 'Sub-division Rain'
                };
                
                sortedKeys.forEach(key => {
                    const score = contribs[key];
                    labels.push(friendlyNames[key] || key);
                    dataValues.push(score);
                    
                    // Green for reducing flood risk (negative), Red for increasing flood risk (positive)
                    if (score >= 0) {
                        backgroundColors.push('rgba(255, 51, 102, 0.45)');
                        borderColors.push('#ff3366');
                    } else {
                        backgroundColors.push('rgba(0, 230, 118, 0.45)');
                        borderColors.push('#00e676');
                    }
                });
                
                // Initialize Chart
                new Chart(chartCanvas, {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Impact on Flood Risk (Hazard Contribution)',
                            data: dataValues,
                            backgroundColor: backgroundColors,
                            borderColor: borderColors,
                            borderWidth: 1.5,
                            borderRadius: 6
                        }]
                    },
                    options: {
                        indexAxis: 'y', // Horizontal bar chart
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: false
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const val = context.parsed.x;
                                        if (val >= 0) {
                                            return ` Increases flood risk (+${val.toFixed(3)})`;
                                        } else {
                                            return ` Decreases flood risk (${val.toFixed(3)})`;
                                        }
                                    }
                                }
                            }
                        },
                        scales: {
                            x: {
                                grid: {
                                    color: 'rgba(255, 255, 255, 0.05)'
                                },
                                ticks: {
                                    color: '#94a3b8'
                                },
                                title: {
                                    display: true,
                                    text: '← DECREASES RISK | INCREASES RISK →',
                                    color: '#94a3b8',
                                    font: {
                                        weight: 'bold'
                                    }
                                }
                            },
                            y: {
                                grid: {
                                    display: false
                                },
                                ticks: {
                                    color: '#f8fafc',
                                    font: {
                                        family: "'Inter', sans-serif"
                                    }
                                }
                            }
                        }
                    }
                });
            } catch (err) {
                console.error("Error building contribution chart:", err);
            }
        }
    }
});
