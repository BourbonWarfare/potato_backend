<?xml version="1.0" encoding="ISO-8859-1"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:template match="text()">
        <xsl:value-of select="."/>
    </xsl:template>
    <xsl:template match="*">
        <xsl:apply-templates/>
    </xsl:template>
    <xsl:template match="/">
        <html>
            <head>
                <title><xsl:value-of select="/squad/name"/></title>
                <link REL="stylesheet" TYPE="text/css" HREF="/static/css/squad.css" />
            </head>
            <body>
                <div class="centeringHeader">
                    <div class="header">
                        <span class="headerItem armaLogo"><a href="https://arma3.com/"><img class="logo" src="/static/img/logo_arma3.png" alt="ArmA3 Logo" /></a></span>
                        <span class="headerItems squadTag"><span class="bracket">[</span><a class="textLink"><xsl:attribute name="href">mailto:<xsl:value-of select="/squad/email"/></xsl:attribute><xsl:value-of select="/squad/@nick" /></a><span class="bracket">]</span></span>
                        <span class="headerItem squadName"><a class="textLink"><xsl:attribute name="href"><xsl:value-of select="/squad/web"/></xsl:attribute><xsl:value-of select="/squad/name"/></a></span>
                        <span class="headerItem squadLogo"><a><xsl:attribute name="href"><xsl:value-of select="/squad/web"/></xsl:attribute><img class="logo" src="/static/img/BW-WebLogo.png" alt="Squad Logo" /></a></span>
                    </div>
                </div>
                <div class="spacer"></div>
                <div class="centeringMemberList">
                    <xsl:for-each select="/squad/member">
                        <div id="{@id}" class="memberInfo">
                            <div class="memberTop">
                                <xsl:choose>
                                    <xsl:when test="email != ''">
                                        <a class="textLink"><xsl:attribute name="href">mailto:<xsl:value-of select="email"/></xsl:attribute>
                                            <span class="linkedNick"><xsl:value-of select="@nick"/></span>
                                            <xsl:if test="name != ''">
                                                <span> (<xsl:value-of select="name"/>)</span>
                                            </xsl:if>
                                        </a>
                                    </xsl:when>
                                    <xsl:otherwise>
                                        <span>
                                            <span class="memberNick"><xsl:value-of select="@nick"/></span>
                                            <xsl:if test="name != ''">
                                                <span class="memberName"> (<xsl:value-of select="name"/>)</span>
                                            </xsl:if>
                                        </span>
                                    </xsl:otherwise>
                                </xsl:choose>
                                <span class="memberId"><a class="textLink"><xsl:attribute name="href">http://steamcommunity.com/profiles/<xsl:value-of select="@id"/></xsl:attribute><xsl:value-of select="@id"/></a></span>
                            </div>
                            <xsl:if test="remark != ''">
                                <div class="memberBottom">
                                    <span class="memberRemark"><xsl:value-of select="remark"/></span>
                                </div>
                            </xsl:if>
                        </div>
                    </xsl:for-each>
                </div>
            </body>
        </html>
    </xsl:template>
</xsl:stylesheet>
