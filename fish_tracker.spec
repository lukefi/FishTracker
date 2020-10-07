# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['main.py'],
             pathex=['D:\\Projects\\VTT\\FishTracking'],
             binaries=[],
             datas=[('detector_parameters.json', '.'),
			 ('file_handlers\\v3\\v3_frame_headers_info.json', 'file_handlers\\v3'),
			 ('file_handlers\\v3\\v3_file_headers_info.json', 'file_handlers\\v3'),
			 ('file_handlers\\v4\\v4_frame_headers_info.json', 'file_handlers\\v4'),
			 ('file_handlers\\v4\\v4_file_headers_info.json', 'file_handlers\\v4'),
			 ('file_handlers\\v5\\v5_frame_headers_info.json', 'file_handlers\\v5'),
			 ('file_handlers\\v5\\v5_file_headers_info.json', 'file_handlers\\v5'),
			 ('libiomp5md.dll', '.')],
             hiddenimports=['sklearn.utils._cython_blas', 'sklearn.neighbors.typedefs', 'sklearn.neighbors.quad_tree', 'sklearn.tree._utils'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
a.datas += Tree('./UI/icons', prefix='UI/icons')

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='fish_tracker',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='fish_tracker')
