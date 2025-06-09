# -*- coding: utf-8 -*-

###########################################################################
## Python code generated with wxFormBuilder (version 4.2.1-0-g80c4cb6)
## http://www.wxformbuilder.org/
##
## PLEASE DO *NOT* EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc
from FileDropTarget import FileDropTarget

import gettext
_ = gettext.gettext

###########################################################################
## Class Main_Ui_Frame
###########################################################################

class Main_Ui_Frame ( wx.Frame ):

    def __init__( self, parent ):
        wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = _(u"图片生成 Word 文档"), pos = wx.DefaultPosition, size = wx.Size( 1000,800 ), style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )

        self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

        main_sizer = wx.BoxSizer( wx.VERTICAL )

        self.MainPanel = wx.Panel( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
        panel_sizer = wx.BoxSizer( wx.HORIZONTAL )

        self.LeftPanel = wx.Panel( self.MainPanel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
        left_sizer = wx.BoxSizer( wx.VERTICAL )

        self.InstructionText = wx.StaticText( self.LeftPanel, wx.ID_ANY, _(u"拖入图片或点击按钮选择图片："), wx.DefaultPosition, wx.DefaultSize, 0 )
        self.InstructionText.Wrap( 0 )

        left_sizer.Add( self.InstructionText, 0, wx.ALL, 5 )

        m_ImageListBoxChoices = []
        self.m_ImageListBox = wx.ListBox( self.LeftPanel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, m_ImageListBoxChoices, wx.LB_EXTENDED )
        left_sizer.Add( self.m_ImageListBox, 1, wx.EXPAND|wx.ALL, 5 )

        left_btn_sizer = wx.BoxSizer( wx.HORIZONTAL )

        self.AddButton = wx.Button( self.LeftPanel, wx.ID_ANY, _(u"选择图片"), wx.DefaultPosition, wx.DefaultSize, 0 )

        self.AddButton.SetDefault()
        self.AddButton.SetAuthNeeded()
        left_btn_sizer.Add( self.AddButton, 0, wx.RIGHT, 5 )

        self.DeleteButton = wx.Button( self.LeftPanel, wx.ID_ANY, _(u"删除选定"), wx.DefaultPosition, wx.DefaultSize, 0 )

        self.DeleteButton.SetDefault()
        self.DeleteButton.SetAuthNeeded()
        left_btn_sizer.Add( self.DeleteButton, 0, wx.RIGHT, 5 )

        self.ClearButton = wx.Button( self.LeftPanel, wx.ID_ANY, _(u"删除全部"), wx.DefaultPosition, wx.DefaultSize, 0 )

        self.ClearButton.SetDefault()
        self.ClearButton.SetAuthNeeded()
        left_btn_sizer.Add( self.ClearButton, 0, wx.RIGHT, 5 )

        self.GenerateButton = wx.Button( self.LeftPanel, wx.ID_ANY, _(u"生成 Word"), wx.DefaultPosition, wx.DefaultSize, 0 )

        self.GenerateButton.SetDefault()
        self.GenerateButton.SetAuthNeeded()
        left_btn_sizer.Add( self.GenerateButton, 0, 0, 0 )


        left_sizer.Add( left_btn_sizer, 0, wx.ALIGN_CENTER|wx.ALL, 10 )


        self.LeftPanel.SetSizer( left_sizer )
        self.LeftPanel.Layout()
        left_sizer.Fit( self.LeftPanel )
        panel_sizer.Add( self.LeftPanel, 1, wx.EXPAND, 0 )

        self.RightPanel = wx.Panel( self.MainPanel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
        right_sizer = wx.BoxSizer( wx.VERTICAL )

        self.PreviewLabel = wx.StaticText( self.RightPanel, wx.ID_ANY, _(u"图片预览："), wx.DefaultPosition, wx.DefaultSize, 0 )
        self.PreviewLabel.Wrap( 0 )

        right_sizer.Add( self.PreviewLabel, 0, wx.LEFT|wx.TOP, 5 )

        self.PreviewBitmap = wx.StaticBitmap( self.RightPanel, wx.ID_ANY, wx.NullBitmap, wx.DefaultPosition, wx.Size( 400,400 ), 0 )
        right_sizer.Add( self.PreviewBitmap, 1, wx.EXPAND|wx.ALL, 5 )


        self.RightPanel.SetSizer( right_sizer )
        self.RightPanel.Layout()
        right_sizer.Fit( self.RightPanel )
        panel_sizer.Add( self.RightPanel, 1, wx.EXPAND, 0 )


        self.MainPanel.SetSizer( panel_sizer )
        self.MainPanel.Layout()
        panel_sizer.Fit( self.MainPanel )
        main_sizer.Add( self.MainPanel, 1, wx.EXPAND |wx.ALL, 5 )


        self.SetSizer( main_sizer )
        self.Layout()
        
        # 初始化文件拖放目标
        self.drop_target = FileDropTarget(self)
        self.m_ImageListBox.SetDropTarget(self.drop_target)

        self.Centre( wx.BOTH )

        # Connect Events
        self.m_ImageListBox.Bind( wx.EVT_LISTBOX, self.on_preview_image )
        self.AddButton.Bind( wx.EVT_BUTTON, self.on_select_files )
        self.DeleteButton.Bind( wx.EVT_BUTTON, self.on_delete_selected )
        self.ClearButton.Bind( wx.EVT_BUTTON, self.on_delete_all )
        self.GenerateButton.Bind( wx.EVT_BUTTON, self.on_generate_doc )

    def __del__( self ):
        pass


    # Virtual event handlers, override them in your derived class
    def on_preview_image( self, event ):
        event.Skip()

    def on_select_files( self, event ):
        event.Skip()

    def on_delete_selected( self, event ):
        event.Skip()

    def on_delete_all( self, event ):
        event.Skip()

    def on_generate_doc( self, event ):
        event.Skip()


