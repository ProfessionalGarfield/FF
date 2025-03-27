	function updateInputFields() {
      const plotType = document.getElementById('plot-type').value;
      const inputsContainer = document.getElementById('plot-inputs');
      inputsContainer.innerHTML = '';
    }

    function addDataPoint() {
      const plotType = document.getElementById('plot-type').value;
      const inputGroup = document.createElement('div');
      inputGroup.className = 'input-group';
      
      // For pie, bar, and radar charts, use category and value inputs.
      if (plotType === 'pie' || plotType === 'bar' || plotType === 'radar') {
        inputGroup.innerHTML = `
          <input type="text" placeholder="Category" class="label-value">
          <input type="number" placeholder="Value" class="value">
          <button class="remove-btn" onclick="this.parentElement.remove()">✕</button>
        `;
      } else {
        inputGroup.innerHTML = `
          <input type="number" placeholder="X Value" class="x-value">
          <input type="number" placeholder="Y Value" class="y-value">
          <button class="remove-btn" onclick="this.parentElement.remove()">✕</button>
        `;
      }
      document.getElementById('plot-inputs').appendChild(inputGroup);
    }
    
    async function generatePlot() {
      const dataPoints = [];
      document.querySelectorAll('.input-group').forEach(group => {
        const plotType = document.getElementById('plot-type').value;
        if (plotType === 'pie' || plotType === 'bar' || plotType === 'radar') {
          const label = group.querySelector('.label-value')?.value.trim();
          const value = parseFloat(group.querySelector('.value')?.value);
          if (label && !isNaN(value)) {
            dataPoints.push({ label, value });
          }
        } else {
          const x = parseFloat(group.querySelector('.x-value')?.value);
          const y = parseFloat(group.querySelector('.y-value')?.value);
          if (!isNaN(x) && !isNaN(y)) {
            dataPoints.push({ x, y });
          }
        }
      });
      
      const plotType = document.getElementById('plot-type').value;
      
      try {
        const response = await fetch('/generate_plot', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ type: plotType, points: dataPoints })
        });
        const data = await response.json();
        document.getElementById('plot-img').src = data.plot_url;
      } catch (error) {
        document.getElementById('plot-container').innerText = 'Error generating plot.';
      }
    }
    
    async function importFile() {
      const fileInput = document.getElementById('file-input');
      if (fileInput.files.length === 0) {
        alert('Please select a file to import.');
        return;
      }
      const formData = new FormData();
      formData.append('file', fileInput.files[0]);
      try {
        const response = await fetch('/upload_data', {
          method: 'POST',
          body: formData
        });
        const data = await response.json();
        if (data.error) {
          document.getElementById('plot-container').innerText = data.error;
        } else if (data.plot_url) {
          document.getElementById('plot-img').src = data.plot_url;
        } else if (data.data) {
          // If server returns data property, call generatePlot() with that data.
          // (Optional: you might decide to dynamically fill inputs or directly generate the plot)
          generatePlotFromData(data.data);
        }
      } catch (error) {
        document.getElementById('plot-container').innerText = 'Error importing file.';
      }
    }
    
    // Optional helper if you want to generate a plot from imported data directly.
    async function generatePlotFromData(dataPoints) {
      const plotType = document.getElementById('plot-type').value;
      try {
        const response = await fetch('/generate_plot', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ type: plotType, points: dataPoints })
        });
        const data = await response.json();
        document.getElementById('plot-img').src = data.plot_url;
      } catch (error) {
        document.getElementById('plot-container').innerText = 'Error generating plot from file.';
      }
    }