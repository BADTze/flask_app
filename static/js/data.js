async function fetchModelEvaluation() {
  try {
    const response = await fetch("/model_evaluation");
    const data = await response.json();
    return data.MAPE;
  } catch (error) {
    console.error("Error fetching model evaluation:", error);
    return null;
  }
}

async function updateModelAccuracy() {
  const mape = await fetchModelEvaluation();
  if (mape !== null) {
    const accuracy = (100 - mape).toFixed(2);

    const modelAccuracyElement = document.getElementById("model-accuracy");
    if (modelAccuracyElement) {
      modelAccuracyElement.textContent = `Akurasi: ${accuracy}%`;
    }
  }
}

async function fetchForecastData() {
  try {
    const response = await fetch("/forecast_data");
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching forecast data:", error);
    return null;
  }
}

async function updateForecastTable() {
  const forecastData = await fetchForecastData();
  if (forecastData) {
    const tableBody = document.querySelector("#forecast-table");
    tableBody.innerHTML = "";
    forecastData.forEach((item) => {
      const row = document.createElement("tr");

      const date = new Date(item.ds);
      const formattedDate = date
        .toLocaleDateString("en-GB", {
          month: "2-digit",
          year: "numeric",
        })
        .replace("/", "-");

      // Kolom DATE
      const dateCell = document.createElement("td");
      dateCell.textContent = formattedDate;
      row.appendChild(dateCell);

      // Kolom Model 1 (yhat)
      const model1Cell = document.createElement("td");
      model1Cell.textContent = item.yhat.toFixed(2);
      row.appendChild(model1Cell);

      // Kolom Model 2 (Jika ada)
      const model2Cell = document.createElement("td");
      model2Cell.textContent = "-";
      row.appendChild(model2Cell);

      tableBody.appendChild(row);
    });
  }
}

const forecastPlot = document.getElementById("forecastPlot");
if (forecastPlot) {
  let chart = echarts.init(forecastPlot);
  let option = {
    title: {
      text: "Forecast Comparison",
      left: "center",
      textStyle: { color: "#f4f4f4", fontSize: 20 },
    },
    tooltip: { trigger: "axis" },
    legend: {
      data: ["model 1", "model 2"],
      top: 30,
      textStyle: { color: "#f4f4f4" },
    },
    xAxis: {
      type: "category",
      data: labels,
      axisLabel: { rotate: -45, color: "#f4f4f4" },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#f4f4f4" },
    },
    series: [
      {
        name: "Model 1",
        type: "line",
        data: model_1,
        color: "#ff4d4d",
        smooth: true,
      },
      {
        name: "Model 2",
        type: "line",
        data: model_2,
        color: "#4d79ff",
        smooth: true,
      },
    ],
  };
  chart.setOption(option);
}

document.addEventListener("DOMContentLoaded", () => {
  updateModelAccuracy();
  updateForecastTable();
});
