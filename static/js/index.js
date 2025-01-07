// 注册 Service Worker
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/js/sw.js')
            .then(registration => {
                console.log('ServiceWorker registration successful');
            })
            .catch(err => {
                console.log('ServiceWorker registration failed:', err);
            });
    });
}

let userCommunityId = null;
let communities = [];
let doors = [];
let supportedDevices = null;

// 添加定时器存储对象
let passwordTimers = {};
let passwordRequests = {}; // 添加请求状态跟踪

// 清除所有密码更新定时器
function clearAllPasswordTimers() {
    Object.values(passwordTimers).forEach(timer => clearTimeout(timer));
    passwordTimers = {};
    passwordRequests = {}; // 清除所有请求状态
}

// 获取URL参数中的token
function getAccessToken() {
    const urlParams = new URLSearchParams(window.location.search);
    let token = urlParams.get('token')
    if (!token) {
        let strs = window.location.href.split(':');
        if (strs.length >= 4) {
            token = strs[3];
        }
    }
    return token;
}

// 添加token到URL
function addTokenToUrl(url) {
    const token = getAccessToken();
    const separator = url.includes('?') ? '&' : '?';
    return `${url}${separator}token=${token}`;
}

// 检查登录状态
async function checkLoginStatus() {
    try {
        const response = await fetch(addTokenToUrl('/check_login'));
        const data = await handleResponse(response);
        if (data > 0) {
            showMainSection();
            await getCommunities();
        }
    } catch (error) {
        console.error('检查登录状态失败:', error);
        showToast(error.message, false);
    }
}

// 获取所有社区信息
async function getCommunities() {
    try {
        const response = await fetch(addTokenToUrl('/get_community_info'));
        const data = await handleResponse(response);
        communities = data;
        updateCommunitySelect();
        
        if (communities && communities.length > 0) {
            const select = document.getElementById('communitySelect');
            select.value = communities[0].communityId;
            await handleCommunityChange();
        }
    } catch (error) {
        showToast(error.message, false);
    }
}

// 更新社区选择下拉框
function updateCommunitySelect() {
    const select = document.getElementById('communitySelect');
    select.innerHTML = '<option value="">请选择社区</option>';
    communities.forEach(community => {
        select.innerHTML += `<option value="${community.communityId}">${community.communityName || community.communityId}</option>`;
    });
}

// 处理社区选择变化
async function handleCommunityChange() {
    const communityId = document.getElementById('communitySelect').value;
    clearAllPasswordTimers(); // 切换社区时清除所有定时器
    if (communityId) {
        userCommunityId = communityId;
        await getDoors(communityId);
    } else {
        document.getElementById('doorList').innerHTML = '';
    }
}

// 获取指定社区的所有门
async function getDoors(communityId) {
    try {
        const response = await fetch(addTokenToUrl(`/get_all_door_info?community_id=${communityId}`));
        const data = await handleResponse(response);
        doors = data;
        updateDoorList();
    } catch (error) {
        showToast(error.message, false);
    }
}

// 获取支持密码设备列表并缓存
async function getSupportedDevices() {
    if (supportedDevices === null) {
        try {
            const response = await fetch(addTokenToUrl('/get_support_password_devices'));
            supportedDevices = await handleResponse(response);
        } catch (error) {
            console.error('获取支持密码设备失败:', error);
            supportedDevices = [];
        }
    }
    return supportedDevices;
}

// 修改计算下一个整10分钟的函数
function getNextMinute() {
    const now = new Date();
    const minutes = now.getMinutes();
    const nextTenMinutes = Math.ceil(minutes / 10) * 10;
    const result = new Date(now);
    result.setMinutes(nextTenMinutes);
    result.setSeconds(0);
    result.setMilliseconds(0);
    return result;
}

// 修改检查设备支持函数
async function checkDeviceSupport(deviceType) {
    const devices = await getSupportedDevices();
    return devices.includes(deviceType);
}

// 修改更新门列表显示函数
async function updateDoorList() {
    const doorList = document.getElementById('doorList');
    doorList.innerHTML = '';
    
    const updateDoorItem = async (door) => {
        const doorDiv = document.createElement('div');
        doorDiv.className = 'door-item';
        const supportPassword = await checkDeviceSupport(door.deviceModel);
        
        doorDiv.innerHTML = `
            <div>${door.doorControlName || '门'}</div>
            <button class="door-button" onclick="openSpecificDoor('${door.doorControlName}', '${door.doorControlId}')">开门</button>
            ${supportPassword ? `
                <div id="password-${door.doorControlId}" class="password-info">
                    <div>密码加载中...</div>
                    <div class="expiry-time"></div>
                </div>
            ` : ''}
        `;
        doorList.appendChild(doorDiv);

        if (supportPassword) {
            await updateDoorPassword(door);
        }
    };

    for (const door of doors.gateDoorList) await updateDoorItem(door);
    for (const door of doors.buildingDoorList) await updateDoorItem(door);
    for (const door of doors.customDoorList) await updateDoorItem(door);
}

// 更新门密码的函数
async function updateDoorPassword(door) {
    const now = new Date();
    const currentMinute = now.getMinutes();
    const currentPeriod = Math.floor(currentMinute / 10);
    const requestKey = `${door.doorControlId}_${currentPeriod}`;
    
    // 检查是否在当前10分钟周期内已发送请求
    if (passwordRequests[requestKey]) {
        return;
    }

    try {
        // 清除该门之前的定时器
        if (passwordTimers[door.doorControlId]) {
            clearTimeout(passwordTimers[door.doorControlId]);
            delete passwordTimers[door.doorControlId];
        }

        // 标记当前周期已发送请求
        passwordRequests[requestKey] = true;

        const response = await fetch(addTokenToUrl(`/get_door_paddword?mac=${door.macAddress}&community_id=${userCommunityId}`));
        const data = await handleResponse(response);
        
        const expiryTime = getNextMinute();
        const passwordElement = document.getElementById(`password-${door.doorControlId}`);
        
        if (passwordElement) {
            passwordElement.innerHTML = `
                <div>密码: ${data.password}</div>
                <div class="expiry-time">有效期至: ${expiryTime.getHours().toString().padStart(2, '0')}:${expiryTime.getMinutes().toString().padStart(2, '0')}</div>
            `;

            // 设置下一次更新的定时器
            let timeUntilNextPeriod = expiryTime - new Date();
            if (timeUntilNextPeriod <= 0) {
                timeUntilNextPeriod = 20_000; // 20秒后再次更新
            }
            passwordTimers[door.doorControlId] = setTimeout(() => {
                delete passwordRequests[requestKey];
                updateDoorPassword(door);
            }, timeUntilNextPeriod + 20_000);
        }
    } catch (error) {
        delete passwordRequests[requestKey];
        console.error('获取开门密码失败:', error);
        addLog(`获取${door.doorControlName}密码失败: ${error.message}`, false);
    }
}

function showToast(message, isSuccess = true) {
    addLog(message, isSuccess);

    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${isSuccess ? 'success' : 'error'} show`;
    
    setTimeout(() => {
        toast.className = 'toast';
    }, 3000);
}

// 开启特定的门
async function openSpecificDoor(doorId) {
    try {
        showLoading();
        if (!userCommunityId) {
            showToast('请先选择社区', false);
            return;
        }
        try {
            const response = await fetch(addTokenToUrl(`/open_door?community_id=${userCommunityId}&door_id=${doorId}`));
            const data = await handleResponse(response);
            if (data.openDoorState) {
                showToast('开门成功');
            } else {
                showToast('开门失败', false);
            }
        } catch (error) {
            showToast(error.message, false);
        }
    } finally {
        hideLoading();
    }
}

// 查询状态
async function checkStatus() {
    if (!userCommunityId) {
        addLog('未获取到社区ID', false);
        return;
    }
    try {
        const response = await fetch(`/get_user_community_expiry_status?community_id=${userCommunityId}`);
        const data = await response.json();
        addLog('状态查询成功: ' + JSON.stringify(data), true);
    } catch (error) {
        console.error('查询状态失败:', error);
        addLog('状态查询失败: ' + error.message, false);
    }
}

// 退出登录
async function doLogout() {
    clearAllPasswordTimers();
    try {
        await fetch('/logout');
        userCommunityId = null;
        showLoginSection();
    } catch (error) {
        console.error('退出失败:', error);
    }
}

function showMainSection() {
    document.getElementById('loginSection').classList.add('hidden');
    document.getElementById('mainSection').classList.remove('hidden');
}

function showLoginSection() {
    document.getElementById('loginSection').classList.remove('hidden');
    document.getElementById('mainSection').classList.add('hidden');
}

function addLog(message, isSuccess = true) {
    const logEntries = document.getElementById('logEntries');
    const timestamp = new Date().toLocaleString();
    const logClass = isSuccess ? 'log-success' : 'log-error';
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${logClass}`;
    logEntry.innerText = `[${timestamp}] ${message}`;
    logEntries.insertBefore(logEntry, logEntries.firstChild);
}

let countdown = 0;
let timer = null;

function updateCountdown() {
    const btn = document.getElementById('sendCodeBtn');
    if (countdown > 0) {
        btn.disabled = true;
        btn.textContent = `${countdown}秒后重试`;
        countdown--;
        timer = setTimeout(updateCountdown, 1000);
    } else {
        btn.disabled = false;
        btn.textContent = '获取验证码';
    }
}

function validatePhone(phone) {
    return /^1[3-9]\d{9}$/.test(phone);
}

document.getElementById('phone').addEventListener('input', function() {
    const btn = document.getElementById('sendCodeBtn');
    if (validatePhone(this.value)) {
        btn.disabled = false;
        btn.classList.add('enabled');
    } else {
        btn.disabled = true;
        btn.classList.remove('enabled');
    }
});

async function sendCode() {
    try {
        showLoading();
        const phone = document.getElementById('phone').value;
        if (!validatePhone(phone)) {
            showToast('请输入正确的手机号', false);
            return;
        }

        try {
            const response = await fetch(addTokenToUrl(`/send_sms_code?phone=${phone}`));
            await handleResponse(response);
            showToast('验证码已发送');
            countdown = 60;
            updateCountdown();
        } catch (error) {
            showToast(error.message, false);
        }
    } finally {
        hideLoading();
    }
}

async function login() {
    try {
        showLoading();
        const phone = document.getElementById('phone').value;
        const code = document.getElementById('code').value;
        
        if (!/^1[3-9]\d{9}$/.test(phone)) {
            showToast('请输入正确的手机号', false);
            return;
        }
        if (!/^\d{6}$/.test(code)) {
            showToast('请输入6位验证码', false);
            return;
        }

        try {
            const response = await fetch(addTokenToUrl(`/login?phone=${phone}&code=${code}`));
            const data = await handleResponse(response);
            if (data.sessionId) {
                showToast('登录成功');
                showMainSection();
                await getCommunities();
            } else {
                showToast('登录失败', false);
            }
        } catch (error) {
            showToast(error.message, false);
        }
    } finally {
        hideLoading();
    }
}

// 页面加载完成后初始化按钮状态
document.addEventListener('DOMContentLoaded', async function() {
    const btn = document.getElementById('sendCodeBtn');
    btn.disabled = true;
    btn.classList.remove('enabled');

    try {
        showLoading();

        // 页面加载时检查登录状态
        await getSupportedDevices();
        await checkLoginStatus();
    } finally {
        hideLoading();
    }
});

async function handleResponse(response) {
    const data = await response.json();
    if (data.code !== 200) {
        throw new Error(data.message || '请求失败');
    }
    return data.data;
}

function showLoading() {
    document.getElementById('loading').classList.add('show');
}

function hideLoading() {
    document.getElementById('loading').classList.remove('show');
}