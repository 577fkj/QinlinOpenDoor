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
let supportedDevices = null;

// 添加定时器存储对象
let passwordTimers = {};

let allUsers = [];
let doors = {};

// 清除所有密码更新定时器
function clearAllPasswordTimers() {
    Object.values(passwordTimers).forEach(timer => clearTimeout(timer));
    passwordTimers = {};
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

// 获取所有用户
async function getAllUser() {
    try {
        const response = await fetch(addTokenToUrl('/get_all_users'));
        const data = await handleResponse(response);
        console.log(data);
        return data;
    } catch (error) {
        console.error('获取用户列表失败:', error);
        showToast(error.message, false);
    }
}

// 更新社区选择下拉框
async function updateCommunitySelect(communities) {
    const select = document.getElementById('communitySelect');
    select.innerHTML = '<option value="">请选择社区</option>';
    let selectedCommunityId = localStorage.getItem('communityId');
    for (const [userId, community] of Object.entries(communities)) {
        const option = document.createElement('option');
        option.value = `${userId}_${community.communityId}`;
        option.textContent = community.customDoorControlName || community.communityName || community.communityId;
        if (selectedCommunityId === option.value) {
            option.selected = true;
        }
        select.appendChild(option);
    }
    if (selectedCommunityId !== null) {
        await handleCommunityChange();
    }
}

// 处理社区选择变化
async function handleCommunityChange() {
    const communityId = document.getElementById('communitySelect').value;
    clearAllPasswordTimers(); // 切换社区时清除所有定时器
    localStorage.setItem('communityId', communityId);
    if (communityId) {
        let data = communityId.split('_');
        await updateDoorList(data[0], data[1]);
    } else {
        document.getElementById('doorList').innerHTML = '';
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

// 计算下一个整10分钟
function getNext10Minute() {
    const now = new Date();
    const minutes = now.getMinutes();
    const next10Minutes = Math.ceil(minutes / 10) * 10;
    now.setMinutes(next10Minutes, 0, 0);
    return now;
}

function getCurrent10Minutes() {
    const now = new Date();
    const minutes = now.getMinutes();
    const current10Minutes = Math.floor(minutes / 10) * 10;
    now.setMinutes(current10Minutes, 0, 0);
    return now;
}

// 修改检查设备支持函数
async function checkDeviceSupport(deviceType) {
    const devices = await getSupportedDevices();
    return devices.includes(deviceType);
}

// 修改更新门列表显示函数
async function updateDoorList(user_id, communityId) {
    const doorList = document.getElementById('doorList');
    doorList.innerHTML = '';
    
    const updateDoorItem = async (door) => {
        const doorDiv = document.createElement('div');
        doorDiv.className = 'door-item';
        const supportPassword = await checkDeviceSupport(door.deviceModel);
        
        doorDiv.innerHTML = `
            <div>${door.doorControlName || '门'}</div>
            <button class="door-button" onclick="openSpecificDoor('${user_id}', '${communityId}', '${door.doorControlName}', '${door.doorControlId}')">开门</button>
            ${supportPassword ? `
                <div id="password-${door.doorControlId}" class="password-info">
                    <div>密码加载中...</div>
                    <div class="expiry-time"></div>
                </div>
            ` : `
                <div class="password-info">
                    <div>此设备不支持密码</div>
                </div>
            `}
        `;
        doorList.appendChild(doorDiv);

        if (supportPassword) {
            await updateDoorPassword(communityId, door);
        }
    };

    for (const door of doors[communityId].gateDoorList) await updateDoorItem(door);
    for (const door of doors[communityId].buildingDoorList) await updateDoorItem(door);
    for (const door of doors[communityId].customDoorList) await updateDoorItem(door);
}

function get_door_password(mac, community_id, timestamp) {
    let s = mac + timestamp + community_id;
    let key = hex_md5(s);
    key = key.replace(/[a-zA-Z]/g, '');
    key = key.slice(-4);
    return key;
}

// 更新门密码
async function updateDoorPassword(userCommunityId, door) {
    try {
        // 清除该门之前的定时器
        if (passwordTimers[door.doorControlId]) {
            clearTimeout(passwordTimers[door.doorControlId]);
            delete passwordTimers[door.doorControlId];
        }

        const expiryTime = getNext10Minute();
        const passwordElement = document.getElementById(`password-${door.doorControlId}`);
        const password = get_door_password(door.macAddress, userCommunityId, getCurrent10Minutes().getTime());
        
        if (passwordElement) {
            passwordElement.innerHTML = `
                <div>密码: ${password}</div>
                <div class="expiry-time">有效期至: ${expiryTime.getHours().toString().padStart(2, '0')}:${expiryTime.getMinutes().toString().padStart(2, '0')}</div>
            `;

            // 设置下一次更新的定时器
            let timeUntilNextPeriod = expiryTime - new Date();
            if (timeUntilNextPeriod <= 0) {
                timeUntilNextPeriod = 5_000; // 5秒后再次更新
            }
            passwordTimers[door.doorControlId] = setTimeout(() => {
                updateDoorPassword(userCommunityId, door);
            }, timeUntilNextPeriod + 5_000);
        }
    } catch (error) {
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
async function openSpecificDoor(user_index, communityId, doorName, doorId) {
    try {
        showLoading();
        try {
            const response = await fetch(addTokenToUrl(`/open_door?user_id=${user_index}&community_id=${communityId}&door_id=${doorId}`));
            const data = await handleResponse(response);
            if (data.openDoorState === 1) {
                showToast(`开门成功(${doorName})`);
            } else {
                showToast(`开门失败(${doorName}): ${data.openDoorState}`, false);
            }
        } catch (error) {
            showToast(error.message, false);
        }
    } finally {
        hideLoading();
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

async function sendCode() {
    try {
        showLoading();
        const phone = document.getElementById('phone').value;
        const loginID = document.getElementById('loginID');
        if (!validatePhone(phone)) {
            showToast('请输入正确的手机号', false);
            return;
        }

        try {
            const response = await fetch(addTokenToUrl(`/send_sms_code?phone=${phone}`));
            let data = await handleResponse(response);
            console.log(data);
            loginID.value = data.index;
            if (data.data.code === 0) {
                showToast('验证码已发送');
                countdown = 60;
                updateCountdown();
            } else {
                showToast(data.data.data.message, false);
            }
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
        const loginID = document.getElementById('loginID').value;
        
        if (!/^1[3-9]\d{9}$/.test(phone)) {
            showToast('请输入正确的手机号', false);
            return;
        }
        if (!/^\d{6}$/.test(code)) {
            showToast('请输入6位验证码', false);
            return;
        }

        try {
            const response = await fetch(addTokenToUrl(`/login?user_id=${loginID}&phone=${phone}&code=${code}`));
            const data = await handleResponse(response);
            if (data.sessionId) {
                showToast('登录成功');
                showMainSection();
                await loadUserInfo();
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

async function loadUserInfo() {
    allUsers = await getAllUser();
        if (allUsers.length > 0) {
            showMainSection();
        }
        let communitys = {};
        for (let user of allUsers) {
            if (user.all_door) {
                for (let communityId in user.all_door) {
                    doors[communityId] = user.all_door[communityId];
                }
            }
            if (user.community_info && user.community_info.length > 0) {
                for (let community of user.community_info) {
                    communitys[user.index] = community;
                }
            }
        }
        await updateCommunitySelect(communitys);
}

// 页面加载完成后初始化按钮状态
document.addEventListener('DOMContentLoaded', async function() {
    const btn = document.getElementById('sendCodeBtn');
    btn.disabled = true;
    btn.classList.remove('enabled');
    const btn2 = document.getElementById('newSendCodeBtn');
    btn2.disabled = true;
    btn2.classList.remove('enabled');

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
    document.getElementById('newPhone').addEventListener('input', function() {
        const btn = document.getElementById('newSendCodeBtn');
        if (validatePhone(this.value)) {
            btn.disabled = false;
            btn.classList.add('enabled');
        } else {
            btn.disabled = true;
            btn.classList.remove('enabled');
        }
    });

    try {
        showLoading();
        await loadUserInfo();
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

function showAccountDialog() {
    const dialog = document.getElementById('accountDialog');
    dialog.style.display = 'flex';
    updateAccountList();
}

function closeAccountDialog() {
    document.getElementById('accountDialog').style.display = 'none';
}

function showAddAccountForm() {
    document.getElementById('addAccountDialog').style.display = 'flex';
}

function closeAddAccountDialog() {
    document.getElementById('addAccountDialog').style.display = 'none';
}

function updateAccountList() {
    const accountList = document.getElementById('accountList');
    accountList.innerHTML = '';
    
    allUsers.forEach(user => {
        const accountItem = document.createElement('div');
        accountItem.className = 'account-item';
        accountItem.innerHTML = `
            <div class="account-info">
                <span class="account-status ${user.is_online ? 'status-online' : 'status-offline'}"></span>
                <span>${user.phone}</span>
            </div>
            <div class="account-actions">
                <button onclick="showReLoginFrom('${user.phone}', '${user.index}')" class="btn" style="width: 100px;">重新登录</button>
                <button onclick="showAccountDetail('${user.phone}')" class="btn">详情</button>
<!--                <button onclick="removeAccount('${user.phone}')" class="btn btn-cancel">删除</button>-->
            </div>
        `;
        accountList.appendChild(accountItem);
    });
}

function showReLoginFrom(phone, id) {
    document.getElementById('reLoginPhone').value = phone;
    document.getElementById('reLoginId').value = id;
    document.getElementById('reLoginCode').value = '';
    let btn = document.getElementById('reLoginSendCodeBtn');
    btn.disabled = false;
    btn.classList.add('enabled');

    document.getElementById('reLoginAccountDialog').style.display = 'flex';
}

function closeReLoginFrom() {
    document.getElementById('reLoginPhone').value = '';
    document.getElementById('reLoginCode').value = '';
    document.getElementById('reLoginId').value = '';
    document.getElementById('reLoginAccountDialog').style.display = 'none';
}

async function sendReLoginAccountCode() {
    const phone = document.getElementById('reLoginPhone').value;
    const reLoginId = document.getElementById('reLoginId').value;
    if (!validatePhone(phone)) {
        showToast('请输入正确的手机号', false);
        return;
    }

    try {
        showLoading();
        const response = await fetch(addTokenToUrl(`/send_sms_code?user_id=${reLoginId}&phone=${phone}`));
        let data = await handleResponse(response);
        console.log(data);
        showToast('验证码已发送');

        // 开始倒计时
        const btn = document.getElementById('reLoginSendCodeBtn');
        btn.disabled = true;
        let countdown = 60;

        const timer = setInterval(() => {
            btn.textContent = `${countdown}秒后重试`;
            countdown--;
            if (countdown < 0) {
                clearInterval(timer);
                btn.disabled = false;
                btn.textContent = '获取验证码';
            }
        }, 1000);
    } catch (error) {
        showToast(error.message, false);
    } finally {
        hideLoading();
    }
}

async function reLoginAccount() {
    const phone = document.getElementById('reLoginPhone').value;
    const code = document.getElementById('reLoginCode').value;
    const reLoginID = document.getElementById('reLoginId').value;

    try {
        showLoading();
        const response = await fetch(addTokenToUrl(`/login?user_id=${reLoginID}&phone=${phone}&code=${code}`));
        const data = await handleResponse(response);
        console.log(data);
        showToast('重新登录成功');

        // 刷新账号列表
        await loadUserInfo();
        updateAccountList();
        closeReLoginFrom();

        // 清空表单
        document.getElementById('reLoginPhone').value = '';
        document.getElementById('reLoginCode').value = '';
        document.getElementById('reLoginId').value = '';
    } catch (error) {
        showToast(error.message, false);
    } finally {
        hideLoading();
    }
}

// 添加新函数
function showAccountDetail(phone) {
    const user = allUsers.find(u => u.phone === phone);
    if (!user) return;

    const detailContent = document.getElementById('accountDetailContent');
    detailContent.innerHTML = `
        <div class="detail-item">
            <div class="detail-label">手机号:</div>
            <div class="detail-value">${user.phone}</div>
        </div>
        <div class="detail-item">
            <div class="detail-label">真名:</div>
            <div class="detail-value">${user.user_info.realName || '未知'}</div>
        </div>
        <div class="detail-item">
            <div class="detail-label">用户名:</div>
            <div class="detail-value">${user.user_info.userName || '未知'}</div>
        </div>
        <div class="detail-item">
            <div class="detail-label">状态:</div>
            <div class="detail-value">${user.is_online ? '在线' : '离线'}</div>
        </div>
        <div class="detail-item">
            <div class="detail-label">是否录入人脸:</div>
            <div class="detail-value">${user.user_info.hasFaceKey === 1 ? '已录入' : '未录入'}</div>
        </div>
        <div class="detail-item">
            <div class="detail-label">可用社区:</div>
            <div class="detail-value">${user.community_info ? user.community_info.map(c => c.communityName).join(', ') : '无'}</div>
        </div>
    `;

    document.getElementById('accountDetailDialog').style.display = 'flex';
}

function closeAccountDetailDialog() {
    document.getElementById('accountDetailDialog').style.display = 'none';
}

async function addAccount() {
    const phone = document.getElementById('newPhone').value;
    const code = document.getElementById('newCode').value;
    const newID = document.getElementById('newID').value;
    
    try {
        showLoading();
        const response = await fetch(addTokenToUrl(`/login?user_id=${newID}&phone=${phone}&code=${code}`));
        const data = await handleResponse(response);
        console.log(data);
        showToast('添加账号成功');
        
        // 刷新账号列表
        await loadUserInfo();
        closeAddAccountDialog();
        
        // 清空表单
        document.getElementById('newPhone').value = '';
        document.getElementById('newCode').value = '';
        document.getElementById('newID').value = '';
    } catch (error) {
        showToast(error.message, false);
    } finally {
        hideLoading();
    }
}

// async function removeAccount(phone) {
//     if (!confirm('确定要删除该账号吗？')) {
//         return;
//     }
//
//     try {
//         showLoading();
//         const response = await fetch(addTokenToUrl(`/remove_account?phone=${phone}`));
//         const data = await handleResponse(response);
//         showToast('删除账号成功');
//
//         // 刷新账号列表
//         allUsers = await getAllUser();
//         updateAccountList();
//     } catch (error) {
//         showToast(error.message, false);
//     } finally {
//         hideLoading();
//     }
// }

async function sendNewAccountCode() {
    const phone = document.getElementById('newPhone').value;
    const newID = document.getElementById('newID');
    if (!validatePhone(phone)) {
        showToast('请输入正确的手机号', false);
        return;
    }
    
    try {
        showLoading();
        const response = await fetch(addTokenToUrl(`/send_sms_code?phone=${phone}`));
        let data = await handleResponse(response);
        console.log(data);
        newID.value = data.index;
        showToast('验证码已发送');
        
        // 开始倒计时
        const btn = document.getElementById('newSendCodeBtn');
        btn.disabled = true;
        let countdown = 60;
        
        const timer = setInterval(() => {
            btn.textContent = `${countdown}秒后重试`;
            countdown--;
            if (countdown < 0) {
                clearInterval(timer);
                btn.disabled = false;
                btn.textContent = '获取验证码';
            }
        }, 1000);
    } catch (error) {
        showToast(error.message, false);
    } finally {
        hideLoading();
    }
}