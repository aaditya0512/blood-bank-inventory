
const BASE_API_URL = 'https://pg7i57nyhh.execute-api.us-east-1.amazonaws.com/dev/'; 

const GET_API_URL = BASE_API_URL + 'status';
const POST_API_URL = BASE_API_URL + 'inventory';

const inventoryList = document.getElementById('inventory-list');
const lastUpdatedSpan = document.getElementById('last-updated');
const updateForm = document.getElementById('update-form');
const bloodTypeSelect = document.getElementById('bloodType');
const formMessage = document.getElementById('form-message');

function getStatusClass(currentStock, safetyThreshold) {
    if (currentStock < safetyThreshold) {
        return 'status-RED'; 
    } else if (currentStock < safetyThreshold * 1.5) {
        return 'status-YELLOW';
    } else {
        return 'status-GREEN'; 
    }
}

async function fetchAndRenderInventory() {
    try {

        const currentSelection = bloodTypeSelect.value; 

        const response = await fetch(GET_API_URL);
        const responseBody = await response.json();

        if (responseBody.statusCode !== 200) {
            throw new Error('API returned status code ' + responseBody.statusCode);
        }
        
        const data = JSON.parse(responseBody.body); 

        inventoryList.innerHTML = '';
        const bloodTypes = [];

        data.forEach(item => {
            const bloodType = item.BloodType;
            const currentStock = Number(item.CurrentStock); 
            const safetyThreshold = Number(item.SafetyThreshold); 
            const statusClass = getStatusClass(currentStock, safetyThreshold);
            
            bloodTypes.push(bloodType); 

            const card = document.createElement('div');
            card.className = `stock-card ${statusClass}`;
            card.innerHTML = `
                <h3>${bloodType}</h3>
                <div class="quantity">${currentStock}</div>
                <div class="threshold">Threshold: ${safetyThreshold} units</div>
            `;
            inventoryList.appendChild(card);
        });
        bloodTypeSelect.innerHTML = bloodTypes.map(type => `<option value="${type}">${type}</option>`).join('');

        if (currentSelection) {
            bloodTypeSelect.value = currentSelection;
        }

        lastUpdatedSpan.textContent = new Date().toLocaleTimeString();

    } catch (error) {
        console.error('Error fetching inventory:', error);
        inventoryList.innerHTML = `<p class="status-RED">Failed to load inventory data: ${error.message}. Check browser console for details.</p>`;
    }
}

updateForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    formMessage.classList.add('hidden');
    formMessage.className = '';

    const bloodType = document.getElementById('bloodType').value;
    const unitsQuantity = parseInt(document.getElementById('units').value); 
    const operation = document.getElementById('operation').value;
    
    let unitsChange;
    if (operation === 'usage') {
        unitsChange = unitsQuantity * -1; 
    } else {
        unitsChange = unitsQuantity;
    }
    
    if (isNaN(unitsChange) || unitsChange === 0) {
        formMessage.textContent = "Please enter a valid quantity.";
        formMessage.classList.remove('hidden');
        formMessage.classList.add('message-error');
        return;
    }

    const payload = {
        BloodType: bloodType,
        UnitsChange: unitsChange // Use the calculated signed value
    };

    try {
        const response = await fetch(POST_API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const responseBody = await response.json();
        let result;
        if (responseBody.body) {
            result = JSON.parse(responseBody.body);
        } else {
            result = responseBody; 
        }

        if (response.ok && responseBody.statusCode === 200) {
            formMessage.textContent = `SUCCESS: Stock for ${bloodType} is now ${result.new_stock}. ${result.alert_triggered ? 'ALERT SENT!' : ''}`;
            formMessage.classList.add('message-success');
            fetchAndRenderInventory();
        } else {
            const errorMessage = result.error || responseBody.body || 'Failed to update stock.';
            formMessage.textContent = `ERROR: ${errorMessage}`;
            formMessage.classList.add('message-error');
        }

    } catch (error) {
        console.error('Error submitting update:', error);
        formMessage.textContent = 'API connection error. Check network and CORS.';
        formMessage.classList.add('message-error');
    }
    formMessage.classList.remove('hidden');
});

fetchAndRenderInventory();
setInterval(fetchAndRenderInventory, 5000);
