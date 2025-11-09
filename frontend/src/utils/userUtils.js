/**
 * 用戶工具函數
 */

/**
 * 從用戶名稱或 email 生成縮寫
 * @param {string} displayName - 顯示名稱
 * @param {string} username - 用戶名稱
 * @param {string} email - 電子郵件
 * @returns {string} 用戶名稱縮寫（1-2 個字符）
 */
export const getUserInitials = (displayName, username, email) => {
  // 優先順序: displayName > username > email
  const name = displayName || username || email;
  
  if (!name) return 'U';
  
  // 如果是中文名稱，取最後兩個字
  if (/[\u4e00-\u9fa5]/.test(name)) {
    const chineseChars = name.match(/[\u4e00-\u9fa5]/g);
    if (chineseChars && chineseChars.length >= 2) {
      return chineseChars.slice(-2).join('');
    } else if (chineseChars && chineseChars.length === 1) {
      return chineseChars[0];
    }
  }
  
  // 如果是英文名稱（有空格分隔）
  const nameParts = name.trim().split(/\s+/);
  if (nameParts.length >= 2) {
    // 取第一個和最後一個單字的首字母
    return (nameParts[0][0] + nameParts[nameParts.length - 1][0]).toUpperCase();
  }
  
  // 如果是 email，取 @ 前的前兩個字符
  if (name.includes('@')) {
    const emailPrefix = name.split('@')[0];
    return emailPrefix.substring(0, 2).toUpperCase();
  }
  
  // 其他情況，取前兩個字符
  return name.substring(0, 2).toUpperCase();
};

/**
 * 獲取用戶顯示名稱
 * @param {Object} user - 用戶物件
 * @returns {string} 用戶顯示名稱
 */
export const getUserDisplayName = (user) => {
  if (!user) return '訪客';
  
  return user.display_name || user.username || user.email?.split('@')[0] || '使用者';
};

/**
 * 生成頭像背景顏色（根據用戶 ID 或 email 生成固定顏色）
 * @param {string} identifier - 用戶識別碼（user_id 或 email）
 * @returns {string} 顏色代碼
 */
export const getAvatarColor = (identifier) => {
  if (!identifier) return '#10a37f';
  
  // 使用簡單的哈希函數生成顏色
  let hash = 0;
  for (let i = 0; i < identifier.length; i++) {
    hash = identifier.charCodeAt(i) + ((hash << 5) - hash);
  }
  
  // 預定義的柔和色彩陣列
  const colors = [
    '#10a37f', // 主題綠色
    '#8b5cf6', // 紫色
    '#3b82f6', // 藍色
    '#ec4899', // 粉色
    '#f59e0b', // 橙色
    '#ef4444', // 紅色
    '#14b8a6', // 青色
    '#a855f7', // 紫羅蘭
  ];
  
  const index = Math.abs(hash) % colors.length;
  return colors[index];
};

export default {
  getUserInitials,
  getUserDisplayName,
  getAvatarColor
};

