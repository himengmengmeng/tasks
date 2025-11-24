from django.contrib import admin
from django.urls import path, include
import debug_toolbar
#from main_app import urls as main_app_urls
from django.conf import settings
from django.conf.urls.static import static



# 这行代码会全局隐藏 'View Site' 链接
admin.site.site_url = None
# 修改 Django Admin 站点的标题（浏览器标签页标题）
admin.site.site_title = "Meng Space Admin"
# 修改 Django Admin 站点的头部名称（登录页和管理站点顶部的标题）
admin.site.site_header = "Meng Space"

urlpatterns = [
    
    path('admin/', admin.site.urls),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
    path('__debug__/', include(debug_toolbar.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)







