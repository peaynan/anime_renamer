import re
import os
import sys

def preprocess_filename(filename: str):
    """
    预处理文件名，将常见的分隔符替换为不常用的符号，并保存修剪后的原始文件名和处理后的文件名片段。
    
    参数：
    filename (str): 原始文件名
    
    返回：
    tuple: (修剪后的原文件名, 处理后的文件名, 处理后的文件名片段)
    """
    # 1. 保存原文件名
    ori_filename = filename

    # 2. 定义技术词汇列表
    technical_keywords = [
        '1080p', '720p', '2160p', 'x265', 'x264', 'ac3', 'flac', 'hevc', 'ma10p', 
        'web-dl', 'bdrip', 'webrip', 'big5', 'hi10p', 'aac', 'avc', 'web', 'multisub', 'multi-subs','1080','1920'
    ]
    
    # 3. 修剪原文件名的技术词
    def remove_technical_keywords_and_noise(text: str):
        # 移除 [8位字母数字] 的部分
        text = re.sub(r'\[[a-zA-Z0-9]{8}\]', '', text)
        # 移除技术词汇（忽略大小写）
        for keyword in technical_keywords:
            text = re.sub(rf'{keyword}', '', text, flags=re.IGNORECASE)
        # 替换空的方括号为 "[]"
        text = re.sub(r'\[\s*\]', '[]', text)
        # 清理多余的空格
        text = re.sub(r'\s{2,}', ' ', text).strip()
        return text

    # 修剪后的原文件名
    original_filename = remove_technical_keywords_and_noise(ori_filename)

    # 4. 替换常见的分隔符为一个不常用的符号（仅在 `processed_filename` 中进行）
    processed_filename = (
        original_filename.replace('.', '|')
        .replace('-', '|')
        .replace('_', '|')
        .replace('[', '|')
        .replace(']', '|')
        .replace('(', '|')
        .replace(')', '|')
        .replace('&', '|')
        .replace('/', '|')  # 新增分隔符
    )

    # 5. 根据替换后的符号拆分文件名
    parts = processed_filename.split('|')
    
    # 6. 去除技术词汇（忽略大小写）和空白片段
    parts = [
        part.strip() for part in parts
        if part.strip() and not any(keyword.lower() in part.lower() for keyword in technical_keywords)
    ]
    
    return original_filename, processed_filename, parts



def identify_subtitle_group(original_filename: str, parts: list, subtitle_groups: list):
    """
    识别文件名中的字幕组名。
    
    参数：
    original_filename (str): 原始文件名
    parts (list): 通过预处理函数获得的文件名片段
    subtitle_groups (list): 字幕组库，包含字幕组名称
    
    返回：
    str: 识别到的字幕组名
    """
    # 1. 尝试通过原始文件名进行字幕组匹配
    matched_groups = []

    # 使用原始文件名检查字幕组是否匹配
    for group in subtitle_groups:
        # 精确匹配字幕组名
        if group.lower() in original_filename.lower():
            matched_groups.append(group)
    
    # 如果匹配到多个字幕组，返回连接的字幕组名
    if len(matched_groups) > 1:
        return "&".join(matched_groups)  # 用&连接
    
    # 如果只匹配到一个字幕组，返回该字幕组名
    elif len(matched_groups) == 1:
        return matched_groups[0]
    
    # 2. 如果没有匹配到，尝试通过文件名片段中的关键词识别
    else:
        for part in parts:
            if 'sub' in part.lower() or 'studio' in part.lower():
                return part.strip()  # 返回该片段作为字幕组名
    
     # 3. 如果没有匹配到字幕组，则返回片段中的第一个片段
    if parts:
        return parts[0]  # 返回第一个片段

    # 4. 如果没有片段可供返回，返回默认值
    return "UNKnownSub"

def identify_season(original_filename: str):
    """
    通过文件名识别季数，若未找到季数则默认为01季。

    参数：
    original_filename (str): 原始文件名

    返回：
    str: 识别到的季数（例如 "01"）
    """
    # 更新正则表达式，支持更灵活的季数格式
    season_pattern = re.compile(r'([Ss]eason\s*(\d+)|[Ss](\d+))')  # 匹配 "Season 1", "S01", 或 "s2"
    
    match = season_pattern.search(original_filename)
    if match:
        # 捕获数字部分
        season = match.group(2) or match.group(3)
        return season.zfill(2)  # 确保格式为两位数
    
    # 如果未找到季数，返回默认值
    return "01"
    
def identify_anime_name(processed_parts: list, subtitle_groups: list):
    """
    通过去除字幕组、季信息和集信息后，从文件名片段中识别动漫名。
    如果没有明确的动漫名候选，返回默认值“UnknownAnime”。

    参数：
    processed_parts (list): 通过预处理函数获得的文件名片段
    subtitle_groups (list): 字幕组库，包含字幕组名称

    返回：
    str: 识别到的动漫名
    """
    # 季信息和集信息正则模式
    season_pattern = re.compile(r'\b([Ss]eason\s*(\d{1,2})|[Ss](\d{1,2}))\b', re.IGNORECASE)  # 匹配季信息，例如 "S2", "Season 02"
    episode_pattern = re.compile(r'\b[Ee](p)?(\d{1,2})\b|\b(\d{1,2})\b', re.IGNORECASE)  # 匹配集信息，例如 "Ep10", "10"

    # 去除字幕组名称
    filtered_parts = [
        part for part in processed_parts
        if not any(group.lower() in part.lower() for group in subtitle_groups)
    ]

    # 去除季信息和集信息，仅删除匹配部分
    cleaned_parts = [
        episode_pattern.sub('', season_pattern.sub('', part)).strip() for part in filtered_parts
    ]

    # 如果没有剩余片段，返回默认值
    if not cleaned_parts:
        return "UnknownAnime"

    # 从剩余片段中选择最长的作为动漫名
    anime_name = max(cleaned_parts, key=len)

    return anime_name.strip()
    
def identify_episode(original_filename: str):
    """
    识别文件名中的集数，并确保识别的数字不超过两位。

    参数：
    original_filename (str): 原始文件名

    返回：
    str: 识别到的集数（例如 "01"），如果未找到则返回 "00"
    """
    # 定义集数的正则模式
    episode_patterns = [
        #re.compile(r'\bS\d{1,2}E(\d{1,2})\b', re.IGNORECASE),  # 匹配 "S01E09"，提取 "E09"
        re.compile(r'E(p)?(\d{1,2})', re.IGNORECASE),      # 匹配 "Ep10", "E03"
        re.compile(r'\b第(\d{1,2})话\b'),                      # 匹配 "第10话"
        re.compile(r'\b(\d{1,2})-(\d{1,2})\b'),               # 匹配范围 "01-02"
        re.compile(r'\b(\d{1,2})\b'),                         # 匹配纯数字 "01"
    ]

    # 遍历正则模式进行匹配
    for pattern in episode_patterns:
        for match in pattern.finditer(original_filename):
            # 提取匹配的数字
            if '-' in match.group(0):  # 处理范围，提取第一个数字
                number = match.group(1)
            else:
                number = match.group(len(match.groups()))
            
            # 检查数字是否符合两位数的限制
            if len(number) <= 2:
                return number.zfill(2)

    # 如果没有找到符合条件的集数，返回默认值
    return "01"

def rename_files(input_path: str, subtitle_groups: list):
    """
    递归处理多层文件夹中的文件，支持按文件夹层级缓存动漫信息。
    
    参数：
    input_path (str): 文件或文件夹路径
    subtitle_groups (list): 字幕组库
    """
    if os.path.isfile(input_path):
        # 如果是单个文件，则处理重命名
        rename_file(input_path, subtitle_groups, cache={})
    elif os.path.isdir(input_path):
        # 如果是文件夹，则递归处理文件夹中的所有文件
        folder_cache = {}  # 缓存当前文件夹中的识别结果
        for root, dirs, files in os.walk(input_path):
            # 每进入一个子文件夹清除缓存，确保每层独立处理
            folder_cache.clear()
            for file in files:
                file_path = os.path.join(root, file)
                rename_file(file_path, subtitle_groups, cache=folder_cache)
    else:
        print(f"无效的路径：{input_path}")

def rename_file(file_path: str, subtitle_groups: list, cache: dict):
    """
    重命名单个文件，使用缓存避免重复识别动漫名、季数和字幕组。
    
    参数：
    file_path (str): 文件路径
    subtitle_groups (list): 字幕组库
    cache (dict): 缓存同一路径的识别结果
    """
    # 获取文件名和扩展名
    file_dir, file_name = os.path.split(file_path)
    file_base, file_ext = os.path.splitext(file_name)

    # 调用预处理函数
    original_filename, processed_filename, processed_parts = preprocess_filename(file_base)

    # 如果当前路径已有缓存，则使用缓存值
    if file_dir in cache:
        anime_name = cache[file_dir]['anime_name']
        season = cache[file_dir]['season']
        subtitle_group = cache[file_dir]['subtitle_group']
    else:
        # 识别动漫名、季数和字幕组
        subtitle_group = identify_subtitle_group(file_name, processed_parts, subtitle_groups)
        season = identify_season(original_filename)
        anime_name = identify_anime_name(processed_parts, subtitle_groups)
        
        # 缓存结果
        cache[file_dir] = {
            'anime_name': anime_name,
            'season': season,
            'subtitle_group': subtitle_group
        }

    # 每个文件独立识别集数
    episode = identify_episode(original_filename)

    # 构造新文件名
    new_name = f"{anime_name} - S{season}E{episode} - {subtitle_group}{file_ext}"
    new_path = os.path.join(file_dir, new_name)

    # 重命名文件
    try:
        os.rename(file_path, new_path)
        print(f"重命名成功：{file_path} -> {new_path}")
    except Exception as e:
        print(f"重命名失败：{file_path} -> {new_path}，错误：{e}")

# 示例字幕组库
subtitle_groups = ['VCB-Studio', 'Kamigami', 'FANSUB', 'UHA-WINGS', 'ReinForce', 'DMG', 'SweetSub', 'Nekomoe kissaten', 
                   'Sakurato', 'Airota', 'LPSub', 'KitaujiSub', 'LoliHouse', 'Haruhana', 'KTXP', 'Moozzi2', 'THORA', 
                   'Fussoir', 'LittleBakas', '.subbers project', 'Lilith-Raws', 'NC-Raws', 'FLsnow','DHR', 'MakariHoshiyume', 
                   'TxxZ', 'A.I.R.nesSub','B-Global', '新Sub', 'XKsub', 'SumiSora','Mabors', 'UCCUSS','Skymoon-Raws']


# 检查是否有命令行参数传入
if len(sys.argv) > 1:
    input_path = sys.argv[1]  # 获取拖动到脚本的路径
else:
    # 如果没有传入路径，则要求用户手动输入
    input_path = input("请输入文件或文件夹路径：").strip().strip('"')

rename_files(input_path, subtitle_groups)
